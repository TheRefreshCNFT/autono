/**
 * Wallet Engine Bridge
 * Connects the wallet-core-engine to the browser extension
 */

import { WalletEngine } from '../../../src/wallet-engine';
import { BlockfrostAPI } from '../../../src/cardano/blockfrost-api';
import { BitcoinAPI } from '../../../src/bitcoin/api';
import { NightChainIntegration } from '../../../src/night-chain/simple-adapter';
import { wipeMemory } from '../../../src/utils/security';

export interface WalletCreationParams {
  wordCount?: 12 | 15 | 18 | 21 | 24;
  chains: ('cardano' | 'bitcoin' | 'night')[];
}

export interface WalletAddresses {
  cardano?: string;
  bitcoin?: {
    legacy: string;      // P2PKH - starts with 1
    segwit: string;      // P2WPKH - starts with bc1q
    taproot: string;     // P2TR - starts with bc1p
  };
  night?: string;
}

export interface WalletCreationResult {
  addresses: WalletAddresses;
  requiresBackup: boolean;
  mnemonic?: string; // Only returned if backup not yet performed
}

export interface NightBackupParams {
  mnemonic: string;
  accessKey: string; // 4-12 characters
}

export interface NightBackupResult {
  success: boolean;
  transactionId?: string;
  error?: string;
}

/**
 * Main wallet bridge class
 * Handles all wallet operations for the extension
 */
export class WalletBridge {
  private engine: WalletEngine | null = null;
  private nightChain: NightChainIntegration | null = null;
  private blockfrostApiKey: string;
  private network: 'mainnet' | 'testnet';

  constructor(blockfrostApiKey: string, network: 'mainnet' | 'testnet' = 'mainnet') {
    this.blockfrostApiKey = blockfrostApiKey;
    this.network = network;
    this.initializeEngine();
  }

  /**
   * Initialize wallet engine with proper configuration
   */
  private initializeEngine(): void {
    // Initialize Blockfrost API
    const blockfrostAPI = new BlockfrostAPI({
      projectId: this.blockfrostApiKey,
      network: this.network,
    });

    // Initialize Bitcoin API
    const bitcoinAPI = new BitcoinAPI({
      provider: 'blockstream',
      network: this.network === 'mainnet' ? 'mainnet' : 'testnet',
    });

    // Initialize Night Chain
    this.nightChain = new NightChainIntegration(
      this.network === 'mainnet' ? 'production' : 'testnet'
    );

    // Create wallet engine with Night Chain encryption
    this.engine = new WalletEngine({
      network: this.network,
      cardanoAPI: {
        provider: 'blockfrost',
        projectId: this.blockfrostApiKey,
        network: this.network,
      },
      bitcoinAPI: {
        provider: 'blockstream',
        network: this.network === 'mainnet' ? 'mainnet' : 'testnet',
      },
      blockfrost: {
        projectId: this.blockfrostApiKey,
        network: this.network,
      },
      // CRITICAL: Wire Night Chain encryption
      encryptBeforeStorage: async (data: Uint8Array) => {
        if (!this.nightChain) {
          throw new Error('Night Chain not initialized');
        }
        // This will be used when storing to Night chain
        return data; // Encryption happens in Night Chain integration
      },
      decryptAfterRetrieval: async (data: Uint8Array) => {
        if (!this.nightChain) {
          throw new Error('Night Chain not initialized');
        }
        // This will be used when retrieving from Night chain
        return data; // Decryption happens in Night Chain integration
      },
    });
  }

  /**
   * Create a new wallet with real addresses
   * Returns mnemonic for Night Chain backup
   */
  async createWallet(params: WalletCreationParams): Promise<WalletCreationResult> {
    if (!this.engine) {
      throw new Error('Wallet engine not initialized');
    }

    try {
      // Generate wallet with mnemonic
      const result = await this.engine.createWallet(
        params.chains.filter(c => c !== 'night') as ('cardano' | 'bitcoin')[],
        params.wordCount || 24
      );

      const addresses: WalletAddresses = {};

      // Get Cardano address
      if (result.addresses.cardano) {
        addresses.cardano = result.addresses.cardano;
      }

      // Get all Bitcoin address types
      if (params.chains.includes('bitcoin')) {
        const mnemonicStr = new TextDecoder().decode(result.mnemonic);
        
        // Generate all 3 Bitcoin address types
        const { BitcoinWallet } = await import('../../../src/bitcoin/wallet');
        const btcWallet = new BitcoinWallet(this.network);
        
        const legacyAddr = await btcWallet.generateAddress(result.mnemonic, 'legacy');
        const segwitAddr = await btcWallet.generateAddress(result.mnemonic, 'native-segwit');
        const taprootAddr = await btcWallet.generateAddress(result.mnemonic, 'taproot');

        addresses.bitcoin = {
          legacy: legacyAddr.address,
          segwit: segwitAddr.address,
          taproot: taprootAddr.address,
        };
      }

      // Generate Night wallet address if requested
      if (params.chains.includes('night') && this.nightChain) {
        const nightAddr = await this.nightChain.generateWalletAddress(result.mnemonic);
        addresses.night = nightAddr;
      }

      // Convert mnemonic to string for return
      const mnemonicStr = new TextDecoder().decode(result.mnemonic);

      // IMPORTANT: Do NOT wipe mnemonic yet - caller needs it for Night backup
      
      return {
        addresses,
        requiresBackup: true,
        mnemonic: mnemonicStr, // Return for Night Chain backup
      };
    } catch (error: any) {
      // Production error handling
      throw new Error(`Failed to create wallet: ${error.message}`);
    }
  }

  /**
   * Backup wallet seed to Night Chain with encryption
   * This is the CRITICAL security step after wallet creation
   */
  async backupToNightChain(params: NightBackupParams): Promise<NightBackupResult> {
    if (!this.nightChain) {
      throw new Error('Night Chain not initialized');
    }

    try {
      // Validate access key (4-12 characters)
      if (params.accessKey.length < 4 || params.accessKey.length > 12) {
        return {
          success: false,
          error: 'Access key must be 4-12 characters',
        };
      }

      // Convert mnemonic to Uint8Array
      const encoder = new TextEncoder();
      const mnemonicBytes = encoder.encode(params.mnemonic);

      // Encrypt and store on Night Chain
      const result = await this.nightChain.backupSeedPhrase(
        mnemonicBytes,
        params.accessKey
      );

      if (!result.success) {
        return {
          success: false,
          error: result.error || 'Backup failed',
        };
      }

      // CRITICAL: Verify decryption works BEFORE wiping
      const verified = await this.nightChain.verifySeedPhraseBackup(
        result.transactionId!,
        params.accessKey,
        mnemonicBytes
      );

      if (!verified) {
        return {
          success: false,
          error: 'Backup verification failed',
        };
      }

      // SUCCESS: Wipe plaintext mnemonic from memory
      wipeMemory(mnemonicBytes);

      // Store backup metadata in extension storage
      await chrome.storage.local.set({
        walletBackup: {
          nightChainTxId: result.transactionId,
          backedUpAt: Date.now(),
          verified: true,
        },
      });

      return {
        success: true,
        transactionId: result.transactionId,
      };
    } catch (error: any) {
      // Production error handling
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Recover wallet from Night Chain
   */
  async recoverFromNightChain(txId: string, accessKey: string): Promise<WalletCreationResult> {
    if (!this.nightChain) {
      throw new Error('Night Chain not initialized');
    }

    try {
      // Retrieve and decrypt from Night Chain
      const mnemonic = await this.nightChain.recoverSeedPhrase(txId, accessKey);

      if (!mnemonic) {
        throw new Error('Failed to recover seed phrase from Night Chain');
      }

      // Convert to string
      const mnemonicStr = new TextDecoder().decode(mnemonic);

      // Import wallet with recovered mnemonic
      const addresses = await this.engine!.importWallet({
        mnemonic,
        chains: ['cardano', 'bitcoin'],
      });

      // Generate all Bitcoin address types
      const { BitcoinWallet } = await import('../../../src/bitcoin/wallet');
      const btcWallet = new BitcoinWallet(this.network);
      
      const legacyAddr = await btcWallet.generateAddress(mnemonic, 'legacy');
      const segwitAddr = await btcWallet.generateAddress(mnemonic, 'native-segwit');
      const taprootAddr = await btcWallet.generateAddress(mnemonic, 'taproot');

      // Generate Night address
      const nightAddr = await this.nightChain.generateWalletAddress(mnemonic);

      // Wipe recovered mnemonic
      wipeMemory(mnemonic);

      return {
        addresses: {
          cardano: addresses.cardano,
          bitcoin: {
            legacy: legacyAddr.address,
            segwit: segwitAddr.address,
            taproot: taprootAddr.address,
          },
          night: nightAddr,
        },
        requiresBackup: false, // Already backed up on Night Chain
      };
    } catch (error: any) {
      // Production error handling
      throw new Error(`Failed to recover wallet: ${error.message}`);
    }
  }

  /**
   * Get balance for all chains
   */
  async getBalances(addresses: WalletAddresses): Promise<any> {
    if (!this.engine) {
      throw new Error('Wallet engine not initialized');
    }

    try {
      const balances = await this.engine.getBalances({
        cardano: addresses.cardano,
        bitcoin: addresses.bitcoin?.segwit, // Use SegWit as default
      });

      return balances;
    } catch (error: any) {
      // Production error handling
      throw error;
    }
  }

  /**
   * Get transaction history
   */
  async getTransactionHistory(addresses: WalletAddresses, limit: number = 50): Promise<any> {
    if (!this.engine) {
      throw new Error('Wallet engine not initialized');
    }

    try {
      const history = await this.engine.getTransactionHistory(
        {
          cardano: addresses.cardano,
          bitcoin: addresses.bitcoin?.segwit,
        },
        limit
      );

      return history;
    } catch (error: any) {
      console.error('Failed to get transaction history:', error);
      throw error;
    }
  }

  /**
   * Resolve ADA handle to address
   */
  async resolveADAHandle(handle: string): Promise<string | null> {
    if (!this.engine) {
      throw new Error('Wallet engine not initialized');
    }

    try {
      const result = await this.engine.resolveADAHandle(handle);
      return result?.address || null;
    } catch (error: any) {
      // Production error handling - return null for invalid handle
      return null;
    }
  }

  /**
   * Build transaction (requires temporary mnemonic access via Night Chain)
   */
  async buildTransaction(
    request: {
      chain: 'cardano' | 'bitcoin';
      from: string;
      to: string;
      amount: string;
    },
    nightTxId: string,
    accessKey: string
  ): Promise<any> {
    if (!this.engine || !this.nightChain) {
      throw new Error('Wallet engine or Night Chain not initialized');
    }

    let mnemonic: Uint8Array | null = null;

    try {
      // Retrieve mnemonic from Night Chain
      mnemonic = await this.nightChain.recoverSeedPhrase(nightTxId, accessKey);

      if (!mnemonic) {
        throw new Error('Failed to retrieve seed phrase');
      }

      // Build transaction
      const unsignedTx = await this.engine.buildTransaction(request, mnemonic);

      return unsignedTx;
    } catch (error: any) {
      // Production error handling
      throw error;
    } finally {
      // CRITICAL: Always wipe mnemonic after use
      if (mnemonic) {
        wipeMemory(mnemonic);
      }
    }
  }

  /**
   * Sign and broadcast transaction
   */
  async signAndBroadcastTransaction(
    unsignedTx: any,
    nightTxId: string,
    accessKey: string
  ): Promise<string> {
    if (!this.engine || !this.nightChain) {
      throw new Error('Wallet engine or Night Chain not initialized');
    }

    let mnemonic: Uint8Array | null = null;

    try {
      // Retrieve mnemonic from Night Chain
      mnemonic = await this.nightChain.recoverSeedPhrase(nightTxId, accessKey);

      if (!mnemonic) {
        throw new Error('Failed to retrieve seed phrase');
      }

      // Sign transaction
      const signedTx = await this.engine.signTransaction(unsignedTx, mnemonic);

      // Broadcast transaction
      const txHash = await this.engine.broadcastTransaction(signedTx);

      return txHash;
    } catch (error: any) {
      // Production error handling
      throw error;
    } finally {
      // CRITICAL: Always wipe mnemonic after use
      if (mnemonic) {
        wipeMemory(mnemonic);
      }
    }
  }
}

/**
 * Singleton instance for extension
 */
let walletBridgeInstance: WalletBridge | null = null;

export async function getWalletBridge(): Promise<WalletBridge> {
  if (!walletBridgeInstance) {
    // Get Blockfrost API key from config or storage
    const BLOCKFROST_API_KEY = 'mainnetehvvvJVoJUAz5DFJJz2L9fHZmkXlXTMP';
    walletBridgeInstance = new WalletBridge(BLOCKFROST_API_KEY, 'mainnet');
  }
  return walletBridgeInstance;
}
