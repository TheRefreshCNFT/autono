/**
 * Cardano wallet operations using cardano-serialization-lib
 * Now integrated with Blockfrost API for real blockchain interactions
 */

import * as CardanoWasm from '@emurgo/cardano-serialization-lib-nodejs';
import { generateMnemonic, mnemonicToEntropy, entropyToMnemonic } from 'bip39';
import { CardanoAddress, NetworkType, WalletError, Balance, Transaction } from '../types';
import { SecureContainer, wipeBuffer, wipeMemory } from '../utils/security';
import { BlockfrostAPI, BlockfrostConfig } from './blockfrost-api';

const CARDANO_DERIVATION_PATH = {
  PURPOSE: 1852, // CIP-1852
  COIN_TYPE: 1815, // ADA
  ACCOUNT: 0,
  ROLE_EXTERNAL: 0, // Receiving addresses
  ROLE_INTERNAL: 1, // Change addresses
  ROLE_STAKING: 2, // Staking keys
};

export class CardanoWallet {
  private network: NetworkType;
  private blockfrost: BlockfrostAPI | null = null;

  constructor(network: NetworkType = 'mainnet', blockfrostConfig?: BlockfrostConfig) {
    this.network = network;
    
    // Initialize Blockfrost if config provided
    if (blockfrostConfig) {
      this.blockfrost = new BlockfrostAPI(blockfrostConfig);
    }
  }

  /**
   * Initialize Blockfrost API (can be called after construction)
   */
  initializeBlockfrost(config: BlockfrostConfig): void {
    this.blockfrost = new BlockfrostAPI(config);
  }

  /**
   * Check if Blockfrost is available
   */
  isBlockfrostAvailable(): boolean {
    return this.blockfrost !== null;
  }

  /**
   * Generate a new Cardano wallet from mnemonic
   * @param mnemonic BIP39 mnemonic as Uint8Array (15 or 24 words)
   * @param accountIndex Account index (default: 0)
   * @param addressIndex Address index (default: 0)
   */
  async generateAddress(
    mnemonic: Uint8Array,
    accountIndex: number = 0,
    addressIndex: number = 0
  ): Promise<CardanoAddress> {
    // Convert Uint8Array to string temporarily for bip39 processing
    const decoder = new TextDecoder();
    const mnemonicStr = decoder.decode(mnemonic);
    
    const entropyHex = mnemonicToEntropy(mnemonicStr);
    const entropyBuffer = Buffer.from(entropyHex, 'hex');
    const entropyContainer = new SecureContainer(entropyBuffer);

    try {
      const entropy = entropyContainer.data;
      const rootKey = CardanoWasm.Bip32PrivateKey.from_bip39_entropy(
        entropy,
        Buffer.from('') // Empty password
      );

      // Derive payment key: m/1852'/1815'/account'/0/address
      const accountKey = rootKey
        .derive(this.harden(CARDANO_DERIVATION_PATH.PURPOSE))
        .derive(this.harden(CARDANO_DERIVATION_PATH.COIN_TYPE))
        .derive(this.harden(accountIndex));

      const paymentKey = accountKey
        .derive(CARDANO_DERIVATION_PATH.ROLE_EXTERNAL)
        .derive(addressIndex);

      // Derive staking key: m/1852'/1815'/account'/2/0
      const stakeKey = accountKey
        .derive(CARDANO_DERIVATION_PATH.ROLE_STAKING)
        .derive(0);

      const paymentPubKey = paymentKey.to_public();
      const stakePubKey = stakeKey.to_public();

      // Build base address
      const networkId = this.network === 'mainnet' ? 1 : 0;

      const baseAddr = CardanoWasm.BaseAddress.new(
        networkId,
        CardanoWasm.Credential.from_keyhash(paymentPubKey.to_raw_key().hash()),
        CardanoWasm.Credential.from_keyhash(stakePubKey.to_raw_key().hash())
      );

      const address = baseAddr.to_address().to_bech32();

      // Clean up sensitive data
      rootKey.free();
      accountKey.free();
      paymentKey.free();
      stakeKey.free();

      return {
        address,
        paymentKey: paymentPubKey.to_bech32(),
        stakeKey: stakePubKey.to_bech32()
      };
    } finally {
      entropyContainer.wipe();
    }
  }

  /**
   * Harden a derivation index
   */
  private harden(index: number): number {
    return 0x80000000 + index;
  }

  /**
   * Build an unsigned Cardano transaction
   */
  async buildTransaction(
    fromAddress: string,
    toAddress: string,
    amountLovelace: string,
    utxos: Array<{ txHash: string; index: number; amount: string }>,
    changeAddress: string,
    ttl?: number
  ): Promise<{
    txBody: string;
    fee: string;
    preview: {
      from: string;
      to: string;
      amount: string;
      fee: string;
      total: string;
    };
  }> {
    try {
      const txBuilder = CardanoWasm.TransactionBuilder.new(
        CardanoWasm.TransactionBuilderConfigBuilder.new()
          .fee_algo(
            CardanoWasm.LinearFee.new(
              CardanoWasm.BigNum.from_str('44'),
              CardanoWasm.BigNum.from_str('155381')
            )
          )
          .pool_deposit(CardanoWasm.BigNum.from_str('500000000'))
          .key_deposit(CardanoWasm.BigNum.from_str('2000000'))
          .max_value_size(5000)
          .max_tx_size(16384)
          .coins_per_utxo_byte(CardanoWasm.BigNum.from_str('4310'))
          .build()
      );

      // Add inputs
      const txUnspentOutputs = CardanoWasm.TransactionUnspentOutputs.new();
      let totalInput = BigInt(0);

      for (const utxo of utxos) {
        const txHash = CardanoWasm.TransactionHash.from_bytes(
          Buffer.from(utxo.txHash, 'hex')
        );
        const input = CardanoWasm.TransactionInput.new(txHash, utxo.index);
        const value = CardanoWasm.Value.new(CardanoWasm.BigNum.from_str(utxo.amount));
        const output = CardanoWasm.TransactionOutput.new(
          CardanoWasm.Address.from_bech32(fromAddress),
          value
        );
        const unspentOutput = CardanoWasm.TransactionUnspentOutput.new(input, output);
        txUnspentOutputs.add(unspentOutput);

        totalInput += BigInt(utxo.amount);
      }

      // Add UTXOs to transaction
      txBuilder.add_inputs_from(
        txUnspentOutputs,
        CardanoWasm.CoinSelectionStrategyCIP2.LargestFirstMultiAsset
      );

      // Add output
      const outputAddr = CardanoWasm.Address.from_bech32(toAddress);
      const outputValue = CardanoWasm.Value.new(CardanoWasm.BigNum.from_str(amountLovelace));
      txBuilder.add_output(
        CardanoWasm.TransactionOutput.new(outputAddr, outputValue)
      );

      // Set TTL
      if (ttl) {
        txBuilder.set_ttl(ttl);
      }

      // Add change address and calculate fee
      const changeAddr = CardanoWasm.Address.from_bech32(changeAddress);
      txBuilder.add_change_if_needed(changeAddr);

      const txBody = txBuilder.build();
      const fee = txBody.fee().to_str();
      const total = (BigInt(amountLovelace) + BigInt(fee)).toString();

      return {
        txBody: Buffer.from(txBody.to_bytes()).toString('hex'),
        fee,
        preview: {
          from: fromAddress,
          to: toAddress,
          amount: amountLovelace,
          fee,
          total
        }
      };
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  /**
   * Sign a transaction
   */
  async signTransaction(
    txBodyHex: string,
    mnemonic: Uint8Array,
    accountIndex: number = 0,
    addressIndex: number = 0
  ): Promise<string> {
    // Convert Uint8Array to string temporarily for bip39 processing
    const decoder = new TextDecoder();
    const mnemonicStr = decoder.decode(mnemonic);
    
    const entropyHex = mnemonicToEntropy(mnemonicStr);
    const entropyBuffer = Buffer.from(entropyHex, 'hex');
    const entropyContainer = new SecureContainer(entropyBuffer);

    try {
      const entropy = entropyContainer.data;
      const rootKey = CardanoWasm.Bip32PrivateKey.from_bip39_entropy(
        entropy,
        Buffer.from('')
      );

      const accountKey = rootKey
        .derive(this.harden(CARDANO_DERIVATION_PATH.PURPOSE))
        .derive(this.harden(CARDANO_DERIVATION_PATH.COIN_TYPE))
        .derive(this.harden(accountIndex));

      const paymentKey = accountKey
        .derive(CARDANO_DERIVATION_PATH.ROLE_EXTERNAL)
        .derive(addressIndex);

      const txBody = CardanoWasm.TransactionBody.from_bytes(Buffer.from(txBodyHex, 'hex'));
      // Create transaction hash
      const txBodyBytes = txBody.to_bytes();
      const bodyHash = CardanoWasm.TransactionBody.from_bytes(txBodyBytes).to_bytes();
      const txHash = CardanoWasm.TransactionHash.from_bytes(
        Buffer.from(bodyHash).subarray(0, 32)
      );

      const witnesses = CardanoWasm.TransactionWitnessSet.new();
      const vkeyWitnesses = CardanoWasm.Vkeywitnesses.new();

      const vkeyWitness = CardanoWasm.make_vkey_witness(
        txHash,
        paymentKey.to_raw_key()
      );
      vkeyWitnesses.add(vkeyWitness);
      witnesses.set_vkeys(vkeyWitnesses);

      const signedTx = CardanoWasm.Transaction.new(txBody, witnesses, undefined);

      // Clean up
      rootKey.free();
      accountKey.free();
      paymentKey.free();

      return Buffer.from(signedTx.to_bytes()).toString('hex');
    } finally {
      entropyContainer.wipe();
    }
  }

  /**
   * Get balance for an address using Blockfrost
   */
  async getBalance(address: string): Promise<Balance> {
    if (!this.blockfrost) {
      throw new Error('Blockfrost not initialized. Please provide API configuration.');
    }

    try {
      return await this.blockfrost.getBalance(address);
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  /**
   * Get transaction history for an address using Blockfrost
   */
  async getTransactionHistory(address: string, limit: number = 50): Promise<Transaction[]> {
    if (!this.blockfrost) {
      throw new Error('Blockfrost not initialized. Please provide API configuration.');
    }

    try {
      return await this.blockfrost.getTransactionHistory(address, limit);
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  /**
   * Submit a signed transaction using Blockfrost
   */
  async submitTransaction(signedTxHex: string): Promise<string> {
    if (!this.blockfrost) {
      throw new Error('Blockfrost not initialized. Please provide API configuration.');
    }

    try {
      return await this.blockfrost.submitTransaction(signedTxHex);
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  /**
   * Resolve ADA Handle ($handle) to address using Blockfrost
   */
  async resolveAdaHandle(handle: string): Promise<string | null> {
    if (!this.blockfrost) {
      throw new Error('Blockfrost not initialized. Please provide API configuration.');
    }

    try {
      return await this.blockfrost.resolveAdaHandle(handle);
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  /**
   * Get UTXOs for transaction building using Blockfrost
   */
  async getUTXOs(address: string) {
    if (!this.blockfrost) {
      throw new Error('Blockfrost not initialized. Please provide API configuration.');
    }

    try {
      return await this.blockfrost.getUTXOs(address);
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  /**
   * Get latest block info for TTL calculation using Blockfrost
   */
  async getLatestBlock() {
    if (!this.blockfrost) {
      throw new Error('Blockfrost not initialized. Please provide API configuration.');
    }

    try {
      return await this.blockfrost.getLatestBlock();
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  /**
   * Estimate transaction fees using Blockfrost
   */
  async estimateFees() {
    if (!this.blockfrost) {
      throw new Error('Blockfrost not initialized. Please provide API configuration.');
    }

    try {
      return await this.blockfrost.estimateFees();
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  /**
   * Get asset metadata using Blockfrost
   */
  async getAssetMetadata(assetId: string) {
    if (!this.blockfrost) {
      throw new Error('Blockfrost not initialized. Please provide API configuration.');
    }

    try {
      return await this.blockfrost.getAssetMetadata(assetId);
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  private handleError(error: any): WalletError {
    return {
      code: 'CARDANO_ERROR',
      message: error.message || 'Cardano operation failed',
      details: error
    };
  }
}
