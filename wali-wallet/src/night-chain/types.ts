/**
 * Type definitions for Night/Midnight blockchain integration
 */

export interface NightWalletConfig {
  network: 'mainnet' | 'testnet' | 'devnet';
  rpcEndpoint?: string;
}

export interface NightWallet {
  address: string;
  publicKey: string;
  // Private key never exposed, only used internally
}

export interface EncryptedAsset {
  assetId: string; // On-chain asset identifier
  encryptedPayload: string; // Base64 encoded encrypted data
  nonce: string; // Initialization vector for AES-GCM
  salt: string; // Salt used for key derivation
  authTag: string; // Authentication tag for GCM
  createdAt: number;
  metadata: {
    version: string; // Encryption scheme version
    keyDerivation: 'PBKDF2-SHA256';
    iterations: number;
    algorithm: 'AES-256-GCM';
  };
}

export interface SeedPhraseBundle {
  version?: string; // Version of the bundle format
  cardanoMnemonic?: string;
  bitcoinMnemonic?: string;
  timestamp: number;
  checksum?: string; // Optional integrity check
}

export interface RecoveryChallenge {
  challengeId: string;
  userWords: string[]; // 4 words from user mnemonic
  botWords: string[]; // 4 words from system
  assetId: string;
  createdAt: number;
}

export interface RecoveryDialogState {
  step: 'user-line-1' | 'bot-line-1' | 'user-line-2' | 'bot-line-2' | 'complete';
  currentPrompt?: string; // Current prompt message for the user
  userLine1?: string; // 4 words
  botLine1?: string; // 4 words
  userLine2?: string; // 4 words
  botLine2?: string; // 4 words
  challengeId: string;
  assetId: string;
  isComplete?: boolean; // Whether the recovery process is complete
  recoveredData?: SeedPhraseBundle; // The decrypted seed phrase bundle (when complete)
}

export interface AccessKeyMetadata {
  attempts: number;
  lastAttempt: number;
  locked: boolean;
  lockUntil?: number;
}

export interface EncryptionResult {
  encryptedData: string; // Base64
  nonce: string; // Base64
  salt: string; // Base64
  authTag: string; // Base64
}

export interface DecryptionResult {
  decryptedData: string; // Plain text
  verified: boolean;
}

export interface NightAssetCreationRequest {
  walletAddress: string;
  encryptedPayload: string;
  metadata: Record<string, any>;
  privateData: boolean; // Whether to use ZK proofs for privacy
}

export interface NightAssetRetrievalRequest {
  assetId: string;
  walletAddress: string;
}

export interface NightTransactionResult {
  txHash: string;
  assetId: string;
  status: 'pending' | 'confirmed' | 'failed';
  blockHeight?: number;
  timestamp: number;
}

export interface KeyDerivationParams {
  accessKey: string; // 4-12 character user key
  salt: Buffer;
  iterations: number; // Default: 100,000
  keyLength: number; // 32 bytes for AES-256
}

export interface SecureStorageMetrics {
  totalAssets: number;
  encryptedSize: number;
  lastBackup?: number;
  recoveryEnabled: boolean;
}
