/**
 * Night Chain Integration - Main Export Module
 * 
 * Secure on-chain storage for seed phrases using:
 * - Midnight/Night blockchain for private data storage
 * - AES-256-GCM encryption with PBKDF2 key derivation
 * - 4-line recovery dialog mechanism
 * - Rate-limited access control (3 strikes)
 */

// Main integration
export { 
  NightChainSecureStorage,
  createNightChainStorage 
} from './integration';

// Wallet management
export { 
  createNightWallet,
  deriveNightWallet,
  validateNightAddress,
  getNetworkFromAddress,
  NightWalletClient
} from './wallet';

// Encryption utilities
export {
  encryptSeedPhrases,
  decryptSeedPhrases,
  verifyEncryptionRoundTrip,
  generateChecksum,
  validateChecksum,
  SecureEncryptionSession
} from './encryption';

// Asset storage
export {
  NightAssetStorage,
  createEncryptedAsset,
  retrieveEncryptedAsset,
  verifyAssetExists,
  deleteAsset
} from './asset-storage';

// Recovery dialog
export {
  RecoveryDialogManager,
  createRecoveryChallenge,
  initializeRecoveryDialog,
  formatRecoveryDialog,
  extractRecoveryPhrase
} from './recovery-dialog';

// Access control
export {
  AccessKeyControl,
  globalAccessControl
} from './access-control';

// Recovery storage (local indexing for wallet recovery)
export {
  RecoveryStorage
} from './recovery-storage';

// Simple adapter (web extension integration)
export {
  NightChainIntegration
} from './simple-adapter';

// Types
export type {
  NightWalletConfig,
  NightWallet,
  EncryptedAsset,
  SeedPhraseBundle,
  RecoveryChallenge,
  RecoveryDialogState,
  AccessKeyMetadata,
  EncryptionResult,
  DecryptionResult,
  NightAssetCreationRequest,
  NightAssetRetrievalRequest,
  NightTransactionResult,
  KeyDerivationParams,
  SecureStorageMetrics
} from './types';
