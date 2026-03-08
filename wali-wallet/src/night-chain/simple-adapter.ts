/**
 * Simple Night Chain Adapter
 * Simplified interface for web extension integration
 */

import { NightChainSecureStorage } from './integration';
import { NightWalletConfig, SeedPhraseBundle, EncryptedAsset } from './types';
import { wipeMemory } from '../utils/security';
import { RecoveryStorage } from './recovery-storage';
import * as bip39 from 'bip39';

export interface BackupResult {
  success: boolean;
  transactionId?: string;
  recoveryPhrase?: string[]; // 16-word recovery phrase
  error?: string;
}

export class NightChainIntegration {
  private storage: NightChainSecureStorage;
  private recoveryStorage: RecoveryStorage;
  private network: 'production' | 'testnet';

  constructor(network: 'production' | 'testnet' = 'production') {
    this.network = network;
    
    // Convert 'production' to 'mainnet' for NightWalletConfig
    const nightNetwork: 'mainnet' | 'testnet' | 'devnet' = 
      network === 'production' ? 'mainnet' : 'testnet';
    
    const config: NightWalletConfig = {
      network: nightNetwork,
      rpcEndpoint: network === 'production' 
        ? 'https://night-mainnet.example.com' 
        : 'https://night-testnet.example.com',
    };

    this.storage = new NightChainSecureStorage(config);
    this.recoveryStorage = new RecoveryStorage(network);
  }

  /**
   * Initialize the Night Chain connection
   */
  async initialize(): Promise<void> {
    await this.storage.initialize();
  }

  /**
   * Generate Night Chain wallet address from mnemonic
   */
  async generateWalletAddress(mnemonic: Uint8Array): Promise<string> {
    // For now, derive from Cardano address (Night uses similar derivation)
    // TODO: Implement proper Night chain address derivation
    const mnemonicStr = new TextDecoder().decode(mnemonic);
    
    // Use Cardano derivation as placeholder
    const { CardanoWallet } = await import('../cardano/wallet');
    const cardanoWallet = new CardanoWallet('mainnet');
    const addr = await cardanoWallet.generateAddress(mnemonic);
    
    // Convert to Night address format (placeholder)
    return 'night1' + addr.address.substring(5, 63);
  }

  /**
   * Backup seed phrase to Night Chain with encryption
   * Also creates a local recovery index for easy wallet recovery
   */
  async backupSeedPhrase(
    mnemonic: Uint8Array,
    accessKey: string
  ): Promise<BackupResult> {
    try {
      // Ensure initialized
      if (!this.storage) {
        await this.initialize();
      }

      // Convert mnemonic to string for encryption
      const mnemonicStr = new TextDecoder().decode(mnemonic);

      // Create seed phrase bundle
      const bundle: SeedPhraseBundle = {
        cardanoMnemonic: mnemonicStr,
        bitcoinMnemonic: mnemonicStr, // Same mnemonic for both
        timestamp: Date.now(),
      };

      // Store on Night Chain (includes encryption verification)
      const result = await this.storage.storeSeedPhrases(bundle, accessKey);

      // Generate 16-word recovery phrase
      const recoveryPhrase = this.generateRecoveryPhrase();

      // Get the encrypted asset data for local caching
      const encryptedAsset = await this.storage.getEncryptedAsset(result.assetId);
      
      if (!encryptedAsset) {
        throw new Error('Failed to retrieve encrypted asset after backup');
      }

      // Index the backup for recovery (local storage)
      await this.recoveryStorage.indexBackup(
        recoveryPhrase,
        result.assetId,
        encryptedAsset,
        {
          hasCardano: !!bundle.cardanoMnemonic,
          hasBitcoin: !!bundle.bitcoinMnemonic,
          hasMidnight: false,
        }
      );

      console.log('[SUCCESS] Backup indexed for recovery');

      return {
        success: true,
        transactionId: result.assetId,
        recoveryPhrase: recoveryPhrase,
      };
    } catch (error: any) {
      console.error('Night Chain backup failed:', error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Generate a 16-word recovery phrase
   * Uses BIP39 wordlist for easy user entry
   */
  private generateRecoveryPhrase(): string[] {
    // Generate 16 words (128 bits of entropy)
    const mnemonic = bip39.generateMnemonic(128); // 12 words = 128 bits
    const words = mnemonic.split(' ');
    
    // Extend to 16 words for better security
    const additionalMnemonic = bip39.generateMnemonic(32); // 3 words = 32 bits
    const additionalWords = additionalMnemonic.split(' ').slice(0, 4);
    
    return [...words, ...additionalWords];
  }

  /**
   * Verify seed phrase backup
   */
  async verifySeedPhraseBackup(
    transactionId: string,
    accessKey: string,
    originalMnemonic: Uint8Array
  ): Promise<boolean> {
    try {
      // Try to recover
      const recovered = await this.recoverSeedPhrase(transactionId, accessKey);
      
      if (!recovered) {
        return false;
      }

      // Compare with original
      const recoveredStr = new TextDecoder().decode(recovered);
      const originalStr = new TextDecoder().decode(originalMnemonic);
      
      const matches = recoveredStr === originalStr;

      // Wipe recovered copy
      wipeMemory(recovered);

      return matches;
    } catch (error) {
      console.error('Verification failed:', error);
      return false;
    }
  }

  /**
   * Recover seed phrase from Night Chain using 16-word recovery phrase
   * 
   * @param recoveryPhrase 16-word recovery phrase given to user during backup
   * @param accessKey User's access key (4-12 characters)
   * @returns Recovered seed phrase as Uint8Array
   */
  async recoverSeedPhraseFromRecovery(
    recoveryPhrase: string[],
    accessKey: string
  ): Promise<Uint8Array | null> {
    try {
      console.log('[INFO] Starting recovery from 16-word phrase');

      // Look up transaction ID from recovery phrase
      const transactionId = await this.recoveryStorage.lookupBackup(recoveryPhrase);

      if (!transactionId) {
        console.error('[ERROR] No backup found for recovery phrase');
        return null;
      }

      console.log('[INFO] Found backup transaction:', transactionId);

      // Retrieve encrypted backup (from local cache)
      const encryptedBackup = await this.recoveryStorage.getEncryptedBackup(transactionId);

      if (!encryptedBackup) {
        console.error('[ERROR] Encrypted backup not found');
        return null;
      }

      // Decrypt using access key
      const bundle = await this.storage.decryptAsset(encryptedBackup, accessKey);

      if (!bundle) {
        console.error('[ERROR] Failed to decrypt backup - invalid access key?');
        return null;
      }

      console.log('[SUCCESS] Wallet recovered successfully');

      // Convert to Uint8Array
      const encoder = new TextEncoder();
      const mnemonic = encoder.encode(bundle.cardanoMnemonic);

      return mnemonic;
    } catch (error: any) {
      console.error('Night Chain recovery failed:', error);
      return null;
    }
  }

  /**
   * Recover seed phrase from Night Chain using transaction ID directly
   * (Legacy method for backwards compatibility)
   */
  async recoverSeedPhrase(
    transactionId: string,
    accessKey: string
  ): Promise<Uint8Array | null> {
    try {
      // Start recovery
      const challengeId = await this.storage.startRecovery(transactionId);

      // Submit access key to 4-line challenge
      // For now, simplified - submit access key directly
      const state = this.storage.submitRecoveryInput(challengeId, accessKey);

      if (!state.isComplete || !state.recoveredData) {
        throw new Error('Recovery incomplete');
      }

      // Get recovered seed phrase bundle
      const bundle = state.recoveredData as SeedPhraseBundle;
      
      // Convert to Uint8Array
      const encoder = new TextEncoder();
      const mnemonic = encoder.encode(bundle.cardanoMnemonic);

      return mnemonic;
    } catch (error: any) {
      console.error('Night Chain recovery failed:', error);
      return null;
    }
  }

  /**
   * Check if access is locked (after too many failed attempts)
   */
  async isAccessLocked(transactionId: string): Promise<boolean> {
    // TODO: Implement lock checking
    return false;
  }
}
