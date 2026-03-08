/**
 * Bitcoin wallet operations using bitcoinjs-lib
 */

import * as bitcoin from 'bitcoinjs-lib';
import { BIP32Factory } from 'bip32';
import { ECPairFactory } from 'ecpair';
import * as ecc from 'tiny-secp256k1';
import { mnemonicToSeedSync } from 'bip39';
import { BitcoinAddress, NetworkType, WalletError } from '../types';
import { SecureContainer, wipeBuffer } from '../utils/security';

const bip32 = BIP32Factory(ecc);
const ECPair = ECPairFactory(ecc);

const BITCOIN_DERIVATION_PATH = {
  PURPOSE_LEGACY: 44,      // P2PKH
  PURPOSE_SEGWIT: 49,      // P2SH-P2WPKH
  PURPOSE_NATIVE_SEGWIT: 84, // P2WPKH (recommended)
  PURPOSE_TAPROOT: 86,     // P2TR (Taproot, BIP-86)
  COIN_TYPE: 0,            // BTC
  ACCOUNT: 0,
};

export type BitcoinAddressType = 'legacy' | 'segwit' | 'native-segwit' | 'taproot';

export class BitcoinWallet {
  private network: bitcoin.Network;
  private networkType: NetworkType;

  constructor(networkType: NetworkType = 'mainnet') {
    this.networkType = networkType;
    this.network = networkType === 'mainnet' 
      ? bitcoin.networks.bitcoin 
      : bitcoin.networks.testnet;
  }

  /**
   * Generate a Bitcoin address from mnemonic
   * @param mnemonic BIP39 mnemonic as Uint8Array
   */
  async generateAddress(
    mnemonic: Uint8Array,
    addressType: BitcoinAddressType = 'native-segwit',
    accountIndex: number = 0,
    addressIndex: number = 0
  ): Promise<BitcoinAddress> {
    // Convert Uint8Array to string temporarily for bip39 processing
    const decoder = new TextDecoder();
    const mnemonicStr = decoder.decode(mnemonic);
    
    const seed = mnemonicToSeedSync(mnemonicStr);
    const seedContainer = new SecureContainer(seed);
    
    try {
      const seedBuffer = Buffer.from(seedContainer.data);
      const root = bip32.fromSeed(seedBuffer);

      const purpose = this.getPurposeFromAddressType(addressType);
      const path = `m/${purpose}'/${BITCOIN_DERIVATION_PATH.COIN_TYPE}'/${accountIndex}'/0/${addressIndex}`;

      const child = root.derivePath(path);
      
      if (!child.publicKey) {
        throw new Error('Failed to derive public key');
      }

      const pubKeyBuffer = Buffer.from(child.publicKey);
      const address = this.getAddressFromPublicKey(pubKeyBuffer, addressType);

      // Wipe seed from memory
      wipeBuffer(seedBuffer);

      return {
        address,
        publicKey: pubKeyBuffer.toString('hex'),
        derivationPath: path
      };
    } finally {
      seedContainer.wipe();
    }
  }

  /**
   * Build an unsigned Bitcoin transaction
   */
  async buildTransaction(
    fromAddress: string,
    toAddress: string,
    amountSatoshis: number,
    utxos: Array<{
      txHash: string;
      index: number;
      amount: number;
      script?: string;
    }>,
    changeAddress: string,
    feeRate: number = 10
  ): Promise<{
    psbt: string;
    fee: number;
    preview: {
      from: string;
      to: string;
      amount: string;
      fee: string;
      total: string;
    };
  }> {
    try {
      const psbt = new bitcoin.Psbt({ network: this.network });

      // Add inputs
      let totalInput = 0;
      for (const utxo of utxos) {
        const payment = bitcoin.payments.p2wpkh({ 
          address: fromAddress, 
          network: this.network 
        });

        psbt.addInput({
          hash: utxo.txHash,
          index: utxo.index,
          witnessUtxo: {
            script: utxo.script 
              ? Buffer.from(utxo.script, 'hex')
              : payment.output!,
            value: utxo.amount
          }
        });
        totalInput += utxo.amount;
      }

      // Add output to recipient
      psbt.addOutput({
        address: toAddress,
        value: amountSatoshis
      });

      // Calculate fee (rough estimate)
      const estimatedSize = utxos.length * 148 + 2 * 34 + 10;
      const fee = Math.ceil(estimatedSize * feeRate);

      // Add change output if needed
      const change = totalInput - amountSatoshis - fee;
      if (change > 546) { // Dust threshold
        psbt.addOutput({
          address: changeAddress,
          value: change
        });
      }

      const psbtBase64 = psbt.toBase64();

      return {
        psbt: psbtBase64,
        fee,
        preview: {
          from: fromAddress,
          to: toAddress,
          amount: amountSatoshis.toString(),
          fee: fee.toString(),
          total: (amountSatoshis + fee).toString()
        }
      };
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  /**
   * Sign a PSBT transaction
   * @param mnemonic BIP39 mnemonic as Uint8Array
   */
  async signTransaction(
    psbtBase64: string,
    mnemonic: Uint8Array,
    addressType: BitcoinAddressType = 'native-segwit',
    accountIndex: number = 0,
    addressIndex: number = 0
  ): Promise<string> {
    // Convert Uint8Array to string temporarily for bip39 processing
    const decoder = new TextDecoder();
    const mnemonicStr = decoder.decode(mnemonic);
    
    const seed = mnemonicToSeedSync(mnemonicStr);
    const seedContainer = new SecureContainer(seed);

    try {
      const seedBuffer = Buffer.from(seedContainer.data);
      const root = bip32.fromSeed(seedBuffer);

      const purpose = this.getPurposeFromAddressType(addressType);
      const path = `m/${purpose}'/${BITCOIN_DERIVATION_PATH.COIN_TYPE}'/${accountIndex}'/0/${addressIndex}`;

      const child = root.derivePath(path);
      
      if (!child.privateKey) {
        throw new Error('Failed to derive private key');
      }

      // Create ECPair from private key
      const keyPair = ECPair.fromPrivateKey(Buffer.from(child.privateKey), {
        network: this.network
      });

      const psbt = bitcoin.Psbt.fromBase64(psbtBase64, { network: this.network });

      // Sign all inputs
      for (let i = 0; i < psbt.data.inputs.length; i++) {
        psbt.signInput(i, keyPair as any); // Type mismatch between ecpair and bitcoinjs-lib
      }

      // Finalize and extract
      psbt.finalizeAllInputs();
      const signedTx = psbt.extractTransaction();

      // Wipe seed from memory
      wipeBuffer(seedBuffer);

      return signedTx.toHex();
    } finally {
      seedContainer.wipe();
    }
  }

  /**
   * Get address from public key based on address type
   */
  private getAddressFromPublicKey(
    publicKey: Buffer,
    addressType: BitcoinAddressType
  ): string {
    let payment;

    switch (addressType) {
      case 'legacy':
        payment = bitcoin.payments.p2pkh({
          pubkey: publicKey,
          network: this.network
        });
        break;
      case 'segwit':
        payment = bitcoin.payments.p2sh({
          redeem: bitcoin.payments.p2wpkh({
            pubkey: publicKey,
            network: this.network
          }),
          network: this.network
        });
        break;
      case 'taproot':
        // Taproot uses x-only pubkey (32 bytes, no prefix)
        const xOnlyPubkey = publicKey.length === 33 
          ? publicKey.slice(1, 33) // Remove first byte if compressed pubkey
          : publicKey;
        payment = bitcoin.payments.p2tr({
          internalPubkey: xOnlyPubkey,
          network: this.network
        });
        break;
      case 'native-segwit':
      default:
        payment = bitcoin.payments.p2wpkh({
          pubkey: publicKey,
          network: this.network
        });
        break;
    }

    if (!payment.address) {
      throw new Error('Failed to generate address');
    }

    return payment.address;
  }

  /**
   * Get BIP44 purpose from address type
   */
  private getPurposeFromAddressType(addressType: BitcoinAddressType): number {
    switch (addressType) {
      case 'legacy':
        return BITCOIN_DERIVATION_PATH.PURPOSE_LEGACY;
      case 'segwit':
        return BITCOIN_DERIVATION_PATH.PURPOSE_SEGWIT;
      case 'taproot':
        return BITCOIN_DERIVATION_PATH.PURPOSE_TAPROOT;
      case 'native-segwit':
      default:
        return BITCOIN_DERIVATION_PATH.PURPOSE_NATIVE_SEGWIT;
    }
  }

  private handleError(error: any): WalletError {
    return {
      code: 'BITCOIN_ERROR',
      message: error.message || 'Bitcoin operation failed',
      details: error
    };
  }
}
