/**
 * Main Night chain integration module
 * 
 * This module orchestrates:
 * 1. Wallet creation
 * 2. Seed phrase encryption
 * 3. On-chain asset storage
 * 4. Recovery mechanism
 * 5. Verification before wiping temp data
 */

import {
  NightWalletConfig,
  NightWallet,
  SeedPhraseBundle,
  EncryptedAsset,
  NightTransactionResult,
  RecoveryDialogState
} from './types';
import { NightWalletClient, createNightWallet } from './wallet';
import { 
  encryptSeedPhrases, 
  decryptSeedPhrases, 
  verifyEncryptionRoundTrip,
  SecureEncryptionSession 
} from './encryption';
import { NightAssetStorage } from './asset-storage';
import { RecoveryDialogManager } from './recovery-dialog';
import { AccessKeyControl } from './access-control';
import { wipeString } from '../utils/security';

/**
 * Complete Night chain integration workflow
 */
export class NightChainSecureStorage {
  private walletClient: NightWalletClient;
  private assetStorage: NightAssetStorage;
  private recoveryManager: RecoveryDialogManager;
  private accessControl: AccessKeyControl;
  private wallet: NightWallet | null = null;
  
  constructor(config: NightWalletConfig) {
    this.walletClient = new NightWalletClient(config);
    this.assetStorage = new NightAssetStorage(config);
    this.recoveryManager = new RecoveryDialogManager();
    this.accessControl = new AccessKeyControl();
  }
  
  /**
   * Initialize the Night chain integration
   */
  async initialize(): Promise<void> {
    console.log('[INFO] Initializing Night chain secure storage');
    
    // Initialize wallet client
    await this.walletClient.initialize();
    
    // Create or load wallet
    this.wallet = await this.walletClient.createWallet();
    
    console.log('[INFO] Night chain integration ready');
    console.log('[INFO] Wallet address:', this.wallet.address);
  }
  
  /**
   * Store seed phrases securely on Night chain
   * 
   * CRITICAL WORKFLOW:
   * 1. Receive seed phrases from wallet-core-engine
   * 2. Encrypt with user's access key
   * 3. Verify encryption works (round-trip test)
   * 4. Store encrypted asset on Night chain
   * 5. Verify asset is accessible
   * 6. Only then wipe plaintext seed phrases
   * 
   * @param bundle Seed phrases to store
   * @param accessKey User's access key (4-12 chars)
   * @returns Transaction result with asset ID
   */
  async storeSeedPhrases(
    bundle: SeedPhraseBundle,
    accessKey: string
  ): Promise<NightTransactionResult> {
    if (!this.wallet) {
      throw new Error('Night wallet not initialized');
    }
    
    console.log('[INFO] Starting secure seed phrase storage');
    console.log('[SECURITY] Access key will never be logged or stored');
    
    // Step 1: Validate access key
    if (!accessKey || accessKey.length < 4 || accessKey.length > 12) {
      throw new Error('Access key must be 4-12 characters');
    }
    
    // Step 2: Encrypt seed phrases
    console.log('[INFO] Encrypting seed phrases with AES-256-GCM');
    const encryptionSession = new SecureEncryptionSession(accessKey);
    
    let encryptedData;
    try {
      encryptedData = encryptionSession.encrypt(bundle);
      
      // Step 3: CRITICAL - Verify encryption works
      console.log('[INFO] Verifying encryption round-trip...');
      const verified = encryptionSession.verify(bundle);
      
      if (!verified) {
        throw new Error('ENCRYPTION_VERIFICATION_FAILED');
      }
      
      console.log('[SUCCESS] Encryption verified successfully');
      
    } finally {
      encryptionSession.close();
    }
    
    // Step 4: Store on Night chain
    console.log('[INFO] Storing encrypted asset on Night blockchain');
    const txResult = await this.assetStorage.storeEncryptedSeedPhrases(
      this.wallet.address,
      encryptedData,
      {
        createdAt: bundle.timestamp,
        hasCardano: !!bundle.cardanoMnemonic,
        hasBitcoin: !!bundle.bitcoinMnemonic
      }
    );
    
    console.log('[SUCCESS] Asset stored on chain');
    console.log('[INFO] Transaction hash:', txResult.txHash);
    console.log('[INFO] Asset ID:', txResult.assetId);
    
    // Step 5: Verify asset is retrievable
    console.log('[INFO] Verifying asset is accessible...');
    const retrievedAsset = await this.assetStorage.getEncryptedAsset(txResult.assetId);
    
    if (!retrievedAsset) {
      throw new Error('ASSET_RETRIEVAL_FAILED - Asset not accessible after storage');
    }
    
    console.log('[SUCCESS] Asset verified accessible on chain');
    
    // Step 6: Now it's safe to wipe plaintext
    console.log('[SECURITY] Wiping plaintext seed phrases from memory');
    if (bundle.cardanoMnemonic) {
      wipeString(bundle.cardanoMnemonic);
    }
    if (bundle.bitcoinMnemonic) {
      wipeString(bundle.bitcoinMnemonic);
    }
    
    console.log('[SUCCESS] Secure storage complete');
    console.log('[INFO] Plaintext wiped, only encrypted on-chain copy remains');
    
    return txResult;
  }
  
  /**
   * Recover seed phrases using recovery dialog
   * 
   * @param assetId Asset ID containing encrypted seed phrases
   * @returns Challenge ID for recovery dialog
   */
  async startRecovery(assetId: string): Promise<string> {
    console.log('[INFO] Starting recovery process for asset:', assetId);
    
    // Verify asset exists
    const asset = await this.assetStorage.getEncryptedAsset(assetId);
    if (!asset) {
      throw new Error('Asset not found');
    }
    
    // Check access control
    const accessCheck = this.accessControl.canAttemptAccess(assetId);
    if (!accessCheck.allowed) {
      throw new Error(accessCheck.reason || 'Access denied');
    }
    
    // Start recovery dialog
    const challengeId = this.recoveryManager.startDialog(assetId);
    
    console.log('[INFO] Recovery dialog started');
    console.log('[INFO] Challenge ID:', challengeId);
    
    return challengeId;
  }
  
  /**
   * Submit user input to recovery dialog
   */
  submitRecoveryInput(challengeId: string, input: string): RecoveryDialogState {
    return this.recoveryManager.submitUserInput(challengeId, input);
  }
  
  /**
   * Get recovery dialog state
   */
  getRecoveryDialog(challengeId: string): RecoveryDialogState | null {
    return this.recoveryManager.getDialog(challengeId);
  }
  
  /**
   * Complete recovery and decrypt seed phrases
   * 
   * @param challengeId Recovery challenge ID
   * @param accessKey User's access key
   * @returns Decrypted seed phrase bundle
   */
  async completeRecovery(
    challengeId: string,
    accessKey: string
  ): Promise<SeedPhraseBundle> {
    console.log('[INFO] Completing recovery process');
    
    // Get dialog state
    const dialog = this.recoveryManager.getDialog(challengeId);
    if (!dialog || dialog.step !== 'complete') {
      throw new Error('Recovery dialog not complete');
    }
    
    // Get asset
    const asset = await this.assetStorage.getEncryptedAsset(dialog.assetId);
    if (!asset) {
      throw new Error('Asset not found');
    }
    
    // Check access control
    const accessCheck = this.accessControl.canAttemptAccess(dialog.assetId);
    if (!accessCheck.allowed) {
      throw new Error(accessCheck.reason || 'Access denied');
    }
    
    // Attempt decryption
    try {
      console.log('[INFO] Attempting decryption with provided access key');
      
      const decrypted = decryptSeedPhrases({
        encryptedData: asset.encryptedPayload,
        nonce: asset.nonce,
        salt: asset.salt,
        authTag: asset.authTag
      }, accessKey);
      
      // Parse bundle
      const bundle: SeedPhraseBundle = JSON.parse(decrypted.decryptedData);
      
      // Record successful access
      this.accessControl.recordSuccessfulAccess(dialog.assetId);
      
      // Complete dialog (cleanup)
      this.recoveryManager.completeDialog(challengeId);
      
      console.log('[SUCCESS] Recovery complete');
      console.log('[INFO] Seed phrases decrypted successfully');
      
      return bundle;
      
    } catch (error: any) {
      // Record failed attempt
      this.accessControl.recordFailedAttempt(dialog.assetId);
      
      const remaining = this.accessControl.getRemainingAttempts(dialog.assetId);
      
      console.error('[ERROR] Decryption failed');
      console.error('[SECURITY] Remaining attempts:', remaining);
      
      if (remaining === 0) {
        console.error('[SECURITY] Asset locked due to too many failed attempts');
      }
      
      throw new Error(`DECRYPTION_FAILED: Invalid access key (${remaining} attempts remaining)`);
    }
  }
  
  /**
   * Get wallet address
   */
  getWalletAddress(): string | null {
    return this.wallet?.address || null;
  }
  
  /**
   * List all stored assets
   */
  listStoredAssets(): EncryptedAsset[] {
    if (!this.wallet) return [];
    return this.assetStorage.listAssets(this.wallet.address);
  }
  
  /**
   * Get access control statistics
   */
  getAccessStats(): any {
    return this.accessControl.getStats();
  }
  
  /**
   * Disconnect and cleanup
   */
  async disconnect(): Promise<void> {
    console.log('[INFO] Disconnecting Night chain integration');
    
    await this.walletClient.disconnect();
    this.assetStorage.clearCache();
    
    console.log('[INFO] Cleanup complete');
  }
}

/**
 * Helper function to create and initialize Night chain storage
 */
export async function createNightChainStorage(
  network: 'mainnet' | 'testnet' | 'devnet' = 'testnet'
): Promise<NightChainSecureStorage> {
  const config: NightWalletConfig = {
    network,
    rpcEndpoint: network === 'devnet' 
      ? 'http://localhost:8545' 
      : `https://${network}.midnight.network`
  };
  
  const storage = new NightChainSecureStorage(config);
  await storage.initialize();
  
  return storage;
}
