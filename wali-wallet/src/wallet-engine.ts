/**
 * Unified Wallet Engine - Main API
 * Coordinates Cardano and Bitcoin wallet operations
 */

import { generateMnemonic } from 'bip39';
import { CardanoWallet } from './cardano/wallet';
import { CardanoAPI, CardanoAPIConfig } from './cardano/api';
import { BlockfrostAPI, BlockfrostConfig } from './cardano/blockfrost-api';
import { BitcoinWallet, BitcoinAddressType } from './bitcoin/wallet';
import { BitcoinAPI, BitcoinAPIConfig } from './bitcoin/api';
import {
  NetworkType,
  WalletCreationResult,
  WalletImportOptions,
  Balance,
  Transaction,
  TransactionBuildRequest,
  UnsignedTransaction,
  SignedTransaction,
  FeeEstimate,
  ADAHandle
} from './types';
import { SecureContainer, validateCardanoAddress, validateBitcoinAddress, sanitizeError, wipeMemory } from './utils/security';

export interface WalletEngineConfig {
  network?: NetworkType;
  cardanoAPI?: CardanoAPIConfig;
  bitcoinAPI?: BitcoinAPIConfig;
  blockfrost?: BlockfrostConfig;
  /**
   * CRITICAL: Function to encrypt data before any disk writes
   * This MUST be provided to ensure no sensitive data is written unencrypted
   */
  encryptBeforeStorage?: (data: Uint8Array) => Promise<Uint8Array>;
  /**
   * CRITICAL: Function to decrypt data after reading from disk
   */
  decryptAfterRetrieval?: (data: Uint8Array) => Promise<Uint8Array>;
}

export class WalletEngine {
  private network: NetworkType;
  private cardanoWallet: CardanoWallet;
  private cardanoAPI?: CardanoAPI;
  private bitcoinWallet: BitcoinWallet;
  private bitcoinAPI?: BitcoinAPI;
  private encryptBeforeStorage?: (data: Uint8Array) => Promise<Uint8Array>;
  private decryptAfterRetrieval?: (data: Uint8Array) => Promise<Uint8Array>;
  private storageAllowed: boolean = false;

  constructor(config: WalletEngineConfig = {}) {
    this.network = config.network || 'mainnet';
    
    // Initialize wallet handlers with Blockfrost if provided
    this.cardanoWallet = new CardanoWallet(this.network, config.blockfrost);
    this.bitcoinWallet = new BitcoinWallet(this.network);

    // Initialize API handlers if configs provided
    if (config.cardanoAPI) {
      this.cardanoAPI = new CardanoAPI(config.cardanoAPI);
    }
    if (config.bitcoinAPI) {
      this.bitcoinAPI = new BitcoinAPI(config.bitcoinAPI);
    }

    // CRITICAL: Set up encryption functions
    this.encryptBeforeStorage = config.encryptBeforeStorage;
    this.decryptAfterRetrieval = config.decryptAfterRetrieval;
    
    // Only allow storage if encryption is configured
    this.storageAllowed = !!(this.encryptBeforeStorage && this.decryptAfterRetrieval);
  }

  /**
   * CRITICAL: Runtime check to prevent unencrypted disk writes
   * This method should be called before ANY storage operation
   */
  private assertEncryptionConfigured(): void {
    if (!this.storageAllowed) {
      throw new Error(
        'SECURITY ERROR: Encryption not configured. Cannot store sensitive data. ' +
        'Configure encryptBeforeStorage and decryptAfterRetrieval in WalletEngineConfig.'
      );
    }
  }

  /**
   * Create a new wallet with mnemonic
   * Returns mnemonic as Uint8Array and initial addresses
   * IMPORTANT: Caller must wipe mnemonic after storing in Night chain (encrypted)
   */
  async createWallet(
    chains: ('cardano' | 'bitcoin')[] = ['cardano', 'bitcoin'],
    wordCount: 12 | 15 | 18 | 21 | 24 = 24
  ): Promise<WalletCreationResult> {
    try {
      // Generate mnemonic based on word count
      const strength = wordCount === 12 ? 128 : 
                      wordCount === 15 ? 160 :
                      wordCount === 18 ? 192 :
                      wordCount === 21 ? 224 : 256;
      
      const mnemonicStr = generateMnemonic(strength);
      
      // Convert to Uint8Array immediately
      const encoder = new TextEncoder();
      const mnemonic = encoder.encode(mnemonicStr);
      
      const addresses: { cardano?: string; bitcoin?: string } = {};

      // Generate addresses for requested chains
      if (chains.includes('cardano')) {
        const cardanoAddr = await this.cardanoWallet.generateAddress(mnemonic);
        addresses.cardano = cardanoAddr.address;
      }

      if (chains.includes('bitcoin')) {
        const bitcoinAddr = await this.bitcoinWallet.generateAddress(mnemonic, 'native-segwit');
        addresses.bitcoin = bitcoinAddr.address;
      }

      return {
        mnemonic, // MUST BE WIPED BY CALLER
        addresses
      };
    } catch (error: any) {
      throw sanitizeError(error);
    }
  }

  /**
   * Import wallet from existing mnemonic
   * @param options.mnemonic BIP39 mnemonic as Uint8Array
   */
  async importWallet(options: WalletImportOptions): Promise<{
    cardano?: string;
    bitcoin?: string;
  }> {
    const mnemonicContainer = new SecureContainer(options.mnemonic);

    try {
      const mnemonic = mnemonicContainer.data;
      const addresses: { cardano?: string; bitcoin?: string } = {};

      if (options.chains.includes('cardano')) {
        const cardanoAddr = await this.cardanoWallet.generateAddress(mnemonic);
        addresses.cardano = cardanoAddr.address;
      }

      if (options.chains.includes('bitcoin')) {
        const bitcoinAddr = await this.bitcoinWallet.generateAddress(mnemonic, 'native-segwit');
        addresses.bitcoin = bitcoinAddr.address;
      }

      return addresses;
    } catch (error: any) {
      throw sanitizeError(error);
    } finally {
      mnemonicContainer.wipe();
    }
  }

  /**
   * Store encrypted mnemonic (CRITICAL: uses Night chain encryption)
   * This is an example of how to properly store sensitive data
   */
  async storeEncryptedMnemonic(mnemonic: Uint8Array, walletId: string): Promise<void> {
    // CRITICAL: Assert encryption is configured before ANY storage
    this.assertEncryptionConfigured();
    
    if (!this.encryptBeforeStorage) {
      throw new Error('Encryption function not available');
    }

    try {
      // Encrypt the mnemonic before storage
      const encrypted = await this.encryptBeforeStorage(mnemonic);
      
      // TODO: Implement actual storage mechanism (e.g., encrypted database)
      // For now, this is a placeholder showing the proper flow:
      // 1. Encrypt FIRST
      // 2. THEN write to storage
      // 3. NEVER write unencrypted data
      
      console.log(`Encrypted mnemonic for wallet ${walletId} (${encrypted.length} bytes)`);
      
      // After storage, wipe the plaintext mnemonic
      wipeMemory(mnemonic);
    } catch (error: any) {
      throw sanitizeError(error);
    }
  }

  /**
   * Retrieve and decrypt mnemonic (CRITICAL: uses Night chain decryption)
   */
  async retrieveEncryptedMnemonic(walletId: string): Promise<Uint8Array> {
    // CRITICAL: Assert encryption is configured
    this.assertEncryptionConfigured();
    
    if (!this.decryptAfterRetrieval) {
      throw new Error('Decryption function not available');
    }

    try {
      // TODO: Implement actual retrieval mechanism
      // For now, this is a placeholder
      const encrypted = new Uint8Array(0); // Retrieve from storage
      
      // Decrypt after retrieval
      const decrypted = await this.decryptAfterRetrieval(encrypted);
      
      return decrypted; // Caller MUST wipe after use
    } catch (error: any) {
      throw sanitizeError(error);
    }
  }

  /**
   * Get unified balance across chains
   */
  async getBalances(addresses: {
    cardano?: string;
    bitcoin?: string;
  }): Promise<Balance[]> {
    const balances: Balance[] = [];

    try {
      if (addresses.cardano && this.cardanoAPI) {
        const cardanoBalance = await this.cardanoAPI.getBalance(addresses.cardano);
        balances.push(cardanoBalance);
      }

      if (addresses.bitcoin && this.bitcoinAPI) {
        const bitcoinBalance = await this.bitcoinAPI.getBalance(addresses.bitcoin);
        balances.push(bitcoinBalance);
      }

      return balances;
    } catch (error: any) {
      throw sanitizeError(error);
    }
  }

  /**
   * Get transaction history across chains
   */
  async getTransactionHistory(
    addresses: { cardano?: string; bitcoin?: string },
    limit: number = 50
  ): Promise<Transaction[]> {
    const transactions: Transaction[] = [];

    try {
      if (addresses.cardano && this.cardanoAPI) {
        const cardanoTxs = await this.cardanoAPI.getTransactionHistory(
          addresses.cardano,
          limit
        );
        transactions.push(...cardanoTxs);
      }

      if (addresses.bitcoin && this.bitcoinAPI) {
        const bitcoinTxs = await this.bitcoinAPI.getTransactionHistory(
          addresses.bitcoin,
          limit
        );
        transactions.push(...bitcoinTxs);
      }

      // Sort by timestamp, most recent first
      return transactions.sort((a, b) => b.timestamp - a.timestamp);
    } catch (error: any) {
      throw sanitizeError(error);
    }
  }

  /**
   * Build an unsigned transaction
   * @param mnemonic BIP39 mnemonic as Uint8Array
   */
  async buildTransaction(
    request: TransactionBuildRequest,
    mnemonic: Uint8Array
  ): Promise<UnsignedTransaction> {
    const mnemonicContainer = new SecureContainer(mnemonic);

    try {
      if (request.chain === 'cardano') {
        if (!this.cardanoAPI) {
          throw new Error('Cardano API not configured');
        }

        // Resolve ADA handle if needed
        let toAddress = request.to;
        if (request.to.startsWith('$')) {
          const resolved = await this.cardanoAPI.resolveADAHandle(request.to);
          if (!resolved) {
            throw new Error(`Failed to resolve ADA handle: ${request.to}`);
          }
          toAddress = resolved;
        }

        // Validate addresses
        if (!validateCardanoAddress(request.from)) {
          throw new Error('Invalid Cardano sender address');
        }
        if (!validateCardanoAddress(toAddress)) {
          throw new Error('Invalid Cardano recipient address');
        }

        // Get UTXOs
        const utxos = await this.cardanoAPI.getUTXOs(request.from);
        
        // Get latest slot for TTL
        const latestBlock = await this.cardanoAPI.getLatestBlock();
        const ttl = latestBlock.slot + 7200; // 2 hours from now

        // Build transaction
        const result = await this.cardanoWallet.buildTransaction(
          request.from,
          toAddress,
          request.amount,
          utxos,
          request.from, // Use same address for change
          ttl
        );

        return {
          chain: 'cardano',
          raw: result.txBody,
          fee: result.fee,
          preview: result.preview
        };

      } else if (request.chain === 'bitcoin') {
        if (!this.bitcoinAPI) {
          throw new Error('Bitcoin API not configured');
        }

        // Validate addresses
        if (!validateBitcoinAddress(request.from)) {
          throw new Error('Invalid Bitcoin sender address');
        }
        if (!validateBitcoinAddress(request.to)) {
          throw new Error('Invalid Bitcoin recipient address');
        }

        // Get UTXOs
        const utxos = await this.bitcoinAPI.getUTXOs(request.from);

        // Get fee estimate
        const fees = await this.bitcoinAPI.estimateFees();
        const feeRate = parseInt(fees.medium);

        // Build transaction
        const result = await this.bitcoinWallet.buildTransaction(
          request.from,
          request.to,
          parseInt(request.amount),
          utxos,
          request.from, // Use same address for change
          feeRate
        );

        return {
          chain: 'bitcoin',
          raw: result.psbt,
          fee: result.fee.toString(),
          preview: result.preview
        };

      } else {
        throw new Error(`Unsupported chain: ${request.chain}`);
      }
    } catch (error: any) {
      throw sanitizeError(error);
    } finally {
      mnemonicContainer.wipe();
    }
  }

  /**
   * Sign a transaction
   * @param mnemonic BIP39 mnemonic as Uint8Array
   */
  async signTransaction(
    unsignedTx: UnsignedTransaction,
    mnemonic: Uint8Array
  ): Promise<SignedTransaction> {
    const mnemonicContainer = new SecureContainer(mnemonic);

    try {
      if (unsignedTx.chain === 'cardano') {
        const signedHex = await this.cardanoWallet.signTransaction(
          unsignedTx.raw,
          mnemonicContainer.data
        );

        return {
          chain: 'cardano',
          txHash: '', // Will be computed after broadcast
          raw: signedHex
        };

      } else if (unsignedTx.chain === 'bitcoin') {
        const signedHex = await this.bitcoinWallet.signTransaction(
          unsignedTx.raw,
          mnemonicContainer.data
        );

        return {
          chain: 'bitcoin',
          txHash: '', // Will be computed after broadcast
          raw: signedHex
        };

      } else {
        throw new Error(`Unsupported chain: ${unsignedTx.chain}`);
      }
    } catch (error: any) {
      throw sanitizeError(error);
    } finally {
      mnemonicContainer.wipe();
    }
  }

  /**
   * Broadcast a signed transaction
   */
  async broadcastTransaction(signedTx: SignedTransaction): Promise<string> {
    try {
      if (signedTx.chain === 'cardano') {
        if (!this.cardanoAPI) {
          throw new Error('Cardano API not configured');
        }
        return await this.cardanoAPI.submitTransaction(signedTx.raw);

      } else if (signedTx.chain === 'bitcoin') {
        if (!this.bitcoinAPI) {
          throw new Error('Bitcoin API not configured');
        }
        return await this.bitcoinAPI.submitTransaction(signedTx.raw);

      } else {
        throw new Error(`Unsupported chain: ${signedTx.chain}`);
      }
    } catch (error: any) {
      throw sanitizeError(error);
    }
  }

  /**
   * Get fee estimates for all chains
   */
  async getFeeEstimates(): Promise<FeeEstimate[]> {
    const estimates: FeeEstimate[] = [];

    try {
      if (this.cardanoAPI) {
        const cardanoFees = await this.cardanoAPI.estimateFees();
        estimates.push({
          chain: 'cardano',
          slow: cardanoFees.slow,
          medium: cardanoFees.medium,
          fast: cardanoFees.fast,
          unit: 'lovelace'
        });
      }

      if (this.bitcoinAPI) {
        const bitcoinFees = await this.bitcoinAPI.estimateFees();
        estimates.push({
          chain: 'bitcoin',
          slow: bitcoinFees.slow,
          medium: bitcoinFees.medium,
          fast: bitcoinFees.fast,
          unit: 'sat/vB'
        });
      }

      return estimates;
    } catch (error: any) {
      throw sanitizeError(error);
    }
  }

  /**
   * Resolve ADA handle to address
   */
  async resolveADAHandle(handle: string): Promise<ADAHandle | null> {
    try {
      if (!this.cardanoAPI) {
        throw new Error('Cardano API not configured');
      }

      const address = await this.cardanoAPI.resolveADAHandle(handle);
      
      if (!address) {
        return null;
      }

      return {
        handle,
        address
      };
    } catch (error: any) {
      throw sanitizeError(error);
    }
  }

  /**
   * Validate an address for a specific chain
   */
  validateAddress(address: string, chain: 'cardano' | 'bitcoin'): boolean {
    if (chain === 'cardano') {
      return validateCardanoAddress(address);
    } else {
      return validateBitcoinAddress(address);
    }
  }
}

export default WalletEngine;
