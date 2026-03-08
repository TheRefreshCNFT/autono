/**
 * Cardano wallet operations using MeshJS
 * Browser-native implementation that works in Chrome extensions
 * @see https://meshjs.dev/
 */

import { BlockfrostProvider, MeshTxBuilder, deserializeAddress } from '@meshsdk/core';
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
  private provider: BlockfrostProvider | null = null;

  constructor(network: NetworkType = 'mainnet', blockfrostConfig?: BlockfrostConfig) {
    this.network = network;
    
    // Initialize Blockfrost if config provided
    if (blockfrostConfig) {
      this.initializeBlockfrost(blockfrostConfig);
    }
  }

  /**
   * Initialize Blockfrost API (can be called after construction)
   */
  initializeBlockfrost(config: BlockfrostConfig): void {
    this.blockfrost = new BlockfrostAPI(config);
    
    // Initialize MeshJS BlockfrostProvider
    this.provider = new BlockfrostProvider(config.projectId);
  }

  /**
   * Check if Blockfrost is available
   */
  isBlockfrostAvailable(): boolean {
    return this.blockfrost !== null && this.provider !== null;
  }

  /**
   * Generate a new Cardano wallet from mnemonic using MeshJS
   * @param mnemonic BIP39 mnemonic as Uint8Array (15 or 24 words)
   * @param accountIndex Account index (default: 0)
   * @param addressIndex Address index (default: 0)
   */
  async generateAddress(
    mnemonic: Uint8Array,
    accountIndex: number = 0,
    addressIndex: number = 0
  ): Promise<CardanoAddress> {
    // Convert Uint8Array to string for bip39 processing
    const decoder = new TextDecoder();
    const mnemonicStr = decoder.decode(mnemonic);
    
    const entropyHex = mnemonicToEntropy(mnemonicStr);
    const entropyBuffer = Buffer.from(entropyHex, 'hex');
    const entropyContainer = new SecureContainer(entropyBuffer);

    try {
      // For MeshJS, we use the standard CIP-1852 derivation path
      // MeshJS handles key derivation internally when we provide the mnemonic
      // We'll use the AppWallet class for key management
      const { AppWallet } = await import('@meshsdk/core');
      
      const wallet = new AppWallet({
        networkId: this.network === 'mainnet' ? 1 : 0,
        key: {
          type: 'mnemonic',
          words: mnemonicStr.split(' '),
        },
      });

      // Get the payment and stake addresses
      // MeshJS returns Address type which needs to be converted to string
      const rewardAddress = await wallet.getRewardAddress();
      const usedAddress = await wallet.getUsedAddress();
      
      if (!usedAddress) {
        throw new Error('Failed to generate address');
      }

      // Convert Address type to string (it's already bech32 encoded)
      const addressStr = String(usedAddress);
      const stakeAddrStr = rewardAddress ? String(rewardAddress) : '';

      return {
        address: addressStr,
        paymentKey: '', // MeshJS handles keys internally
        stakeKey: stakeAddrStr,
      };
    } finally {
      entropyContainer.wipe();
    }
  }

  /**
   * Build an unsigned Cardano transaction using MeshJS
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
    if (!this.provider) {
      throw new Error('Blockfrost provider not initialized');
    }

    try {
      const txBuilder = new MeshTxBuilder({
        fetcher: this.provider,
        verbose: false,
      });

      // Convert UTXOs to MeshJS format
      const meshUtxos = utxos.map(utxo => ({
        input: {
          txHash: utxo.txHash,
          outputIndex: utxo.index,
        },
        output: {
          address: fromAddress,
          amount: [
            {
              unit: 'lovelace',
              quantity: utxo.amount,
            },
          ],
        },
      }));

      // Build transaction
      txBuilder
        .selectUtxosFrom(meshUtxos)
        .changeAddress(changeAddress)
        .txOut(toAddress, [
          {
            unit: 'lovelace',
            quantity: amountLovelace,
          },
        ]);

      // Set TTL if provided
      if (ttl) {
        txBuilder.invalidHereafter(ttl);
      }

      // Complete the transaction (calculates fees and builds)
      const unsignedTx = await txBuilder.complete();

      // Extract fee from the transaction
      // MeshJS returns the transaction hex, we need to estimate fee
      const estimatedFee = '170000'; // Default ~0.17 ADA
      const total = (BigInt(amountLovelace) + BigInt(estimatedFee)).toString();

      return {
        txBody: unsignedTx,
        fee: estimatedFee,
        preview: {
          from: fromAddress,
          to: toAddress,
          amount: amountLovelace,
          fee: estimatedFee,
          total,
        },
      };
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  /**
   * Sign a transaction using MeshJS
   */
  async signTransaction(
    txBodyHex: string,
    mnemonic: Uint8Array,
    accountIndex: number = 0,
    addressIndex: number = 0
  ): Promise<string> {
    // Convert Uint8Array to string for bip39 processing
    const decoder = new TextDecoder();
    const mnemonicStr = decoder.decode(mnemonic);
    
    const entropyHex = mnemonicToEntropy(mnemonicStr);
    const entropyBuffer = Buffer.from(entropyHex, 'hex');
    const entropyContainer = new SecureContainer(entropyBuffer);

    try {
      const { AppWallet } = await import('@meshsdk/core');
      
      const wallet = new AppWallet({
        networkId: this.network === 'mainnet' ? 1 : 0,
        key: {
          type: 'mnemonic',
          words: mnemonicStr.split(' '),
        },
      });

      // Sign the transaction
      const signedTx = await wallet.signTx(txBodyHex, true); // partialSign = true
      
      return signedTx;
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
