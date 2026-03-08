/**
 * Simple Night Chain Adapter
 * Simplified interface for web extension integration
 */

import { NightChainSecureStorage } from './integration';
import { NightWalletConfig, SeedPhraseBundle } from './types';
import { wipeMemory } from '../utils/security';

export interface BackupResult {
  success: boolean;
  transactionId?: string;
  error?: string;
}

export class NightChainIntegration {
  private storage: NightChainSecureStorage;
  private network: 'production' | 'testnet';

  constructor(network: 'production' | 'testnet' = 'production') {
    this.network = network;
    
    const config: NightWalletConfig = {
      network: network,
      rpcEndpoint: network === 'production' 
        ? 'https://night-mainnet.example.com' 
        : 'https://night-testnet.example.com',
    };

    this.storage = new NightChainSecureStorage(config);
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

      // Store on Night Chain
      const result = await this.storage.storeSeedPhrases(bundle, accessKey);

      return {
        success: true,
        transactionId: result.assetId,
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
   * Recover seed phrase from Night Chain
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
