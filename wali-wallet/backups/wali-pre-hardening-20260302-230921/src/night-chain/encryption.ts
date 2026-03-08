/**
 * Encryption/Decryption module using AES-256-GCM with PBKDF2 key derivation
 * 
 * SECURITY REQUIREMENTS:
 * - Access key never logged or stored in plaintext
 * - Encrypted data only decryptable with correct access key
 * - PBKDF2 with 100,000+ iterations for key derivation
 * - Wipe all sensitive data after use
 */

import * as crypto from 'crypto';
import { 
  EncryptionResult, 
  DecryptionResult, 
  KeyDerivationParams,
  SeedPhraseBundle 
} from './types';
import { SecureContainer, wipeBuffer } from '../utils/security';

const DEFAULT_ITERATIONS = 100000; // PBKDF2 iterations
const KEY_LENGTH = 32; // 256 bits for AES-256
const SALT_LENGTH = 32; // 256 bits
const NONCE_LENGTH = 12; // 96 bits for GCM
const AUTH_TAG_LENGTH = 16; // 128 bits

/**
 * Derive encryption key from user access key using PBKDF2
 * @param accessKey User's 4-12 character access key
 * @param salt Random salt for key derivation
 * @param iterations Number of PBKDF2 iterations (default: 100,000)
 * @returns Derived key buffer (32 bytes)
 */
function deriveKey(params: KeyDerivationParams): Buffer {
  const { accessKey, salt, iterations, keyLength } = params;
  
  if (!accessKey || accessKey.length < 4 || accessKey.length > 12) {
    throw new Error('Access key must be 4-12 characters');
  }
  
  // Use PBKDF2 with SHA-256
  const derivedKey = crypto.pbkdf2Sync(
    accessKey,
    salt,
    iterations,
    keyLength,
    'sha256'
  );
  
  return derivedKey;
}

/**
 * Encrypt seed phrase bundle using AES-256-GCM
 * @param bundle Seed phrase bundle to encrypt
 * @param accessKey User's access key (4-12 chars)
 * @returns Encrypted data with metadata
 */
export function encryptSeedPhrases(
  bundle: SeedPhraseBundle,
  accessKey: string
): EncryptionResult {
  // Validate access key
  if (!accessKey || accessKey.length < 4 || accessKey.length > 12) {
    throw new Error('Access key must be 4-12 characters');
  }
  
  // Generate random salt and nonce
  const salt = crypto.randomBytes(SALT_LENGTH);
  const nonce = crypto.randomBytes(NONCE_LENGTH);
  
  // Derive encryption key
  const key = deriveKey({
    accessKey,
    salt,
    iterations: DEFAULT_ITERATIONS,
    keyLength: KEY_LENGTH
  });
  
  try {
    // Serialize bundle to JSON
    const plaintext = JSON.stringify(bundle);
    
    // Create cipher
    const cipher = crypto.createCipheriv('aes-256-gcm', key, nonce);
    
    // Encrypt
    let encrypted = cipher.update(plaintext, 'utf8');
    encrypted = Buffer.concat([encrypted, cipher.final()]);
    
    // Get authentication tag
    const authTag = cipher.getAuthTag();
    
    return {
      encryptedData: encrypted.toString('base64'),
      nonce: nonce.toString('base64'),
      salt: salt.toString('base64'),
      authTag: authTag.toString('base64')
    };
  } finally {
    // Wipe sensitive key material
    wipeBuffer(key);
    wipeBuffer(salt);
    wipeBuffer(nonce);
  }
}

/**
 * Decrypt encrypted seed phrase bundle
 * @param encrypted Encrypted data with metadata
 * @param accessKey User's access key
 * @returns Decrypted seed phrase bundle
 */
export function decryptSeedPhrases(
  encrypted: EncryptionResult,
  accessKey: string
): DecryptionResult {
  // Validate access key
  if (!accessKey || accessKey.length < 4 || accessKey.length > 12) {
    throw new Error('Access key must be 4-12 characters');
  }
  
  // Decode base64 data
  const encryptedBuffer = Buffer.from(encrypted.encryptedData, 'base64');
  const nonce = Buffer.from(encrypted.nonce, 'base64');
  const salt = Buffer.from(encrypted.salt, 'base64');
  const authTag = Buffer.from(encrypted.authTag, 'base64');
  
  // Derive decryption key
  const key = deriveKey({
    accessKey,
    salt,
    iterations: DEFAULT_ITERATIONS,
    keyLength: KEY_LENGTH
  });
  
  try {
    // Create decipher
    const decipher = crypto.createDecipheriv('aes-256-gcm', key, nonce);
    decipher.setAuthTag(authTag);
    
    // Decrypt
    let decrypted = decipher.update(encryptedBuffer);
    decrypted = Buffer.concat([decrypted, decipher.final()]);
    
    const plaintext = decrypted.toString('utf8');
    
    // Parse JSON
    const bundle: SeedPhraseBundle = JSON.parse(plaintext);
    
    return {
      decryptedData: JSON.stringify(bundle),
      verified: true
    };
  } catch (error: any) {
    // Decryption failed - likely wrong access key
    if (error.message.includes('Unsupported state') || 
        error.message.includes('bad decrypt')) {
      throw new Error('INVALID_ACCESS_KEY');
    }
    throw error;
  } finally {
    // Wipe sensitive key material
    wipeBuffer(key);
    wipeBuffer(salt);
    wipeBuffer(nonce);
    wipeBuffer(encryptedBuffer);
  }
}

/**
 * Verify that decryption works before wiping original data
 * This is a critical safety check
 */
export function verifyEncryptionRoundTrip(
  bundle: SeedPhraseBundle,
  accessKey: string
): boolean {
  try {
    // Encrypt
    const encrypted = encryptSeedPhrases(bundle, accessKey);
    
    // Decrypt
    const decrypted = decryptSeedPhrases(encrypted, accessKey);
    
    // Verify contents match
    const originalJson = JSON.stringify(bundle);
    const recoveredJson = decrypted.decryptedData;
    
    return originalJson === recoveredJson && decrypted.verified;
  } catch (error) {
    console.error('Encryption round-trip verification failed:', error);
    return false;
  }
}

/**
 * Generate a cryptographically secure checksum for bundle integrity
 */
export function generateChecksum(bundle: SeedPhraseBundle): string {
  const data = JSON.stringify(bundle);
  return crypto.createHash('sha256').update(data).digest('hex');
}

/**
 * Validate checksum
 */
export function validateChecksum(bundle: SeedPhraseBundle, checksum: string): boolean {
  const computed = generateChecksum(bundle);
  return computed === checksum;
}

/**
 * Secure wrapper for encryption operations with auto-cleanup
 */
export class SecureEncryptionSession {
  private accessKeyContainer: SecureContainer<Buffer> | null = null;
  private originalKey: string;
  
  constructor(accessKey: string) {
    this.originalKey = accessKey;
    const keyBuffer = Buffer.from(accessKey, 'utf-8');
    this.accessKeyContainer = new SecureContainer(keyBuffer);
  }
  
  encrypt(bundle: SeedPhraseBundle): EncryptionResult {
    if (!this.accessKeyContainer || this.accessKeyContainer.isWiped()) {
      throw new Error('Encryption session has been closed');
    }
    const keyString = this.accessKeyContainer.data.toString('utf-8');
    return encryptSeedPhrases(bundle, keyString);
  }
  
  decrypt(encrypted: EncryptionResult): DecryptionResult {
    if (!this.accessKeyContainer || this.accessKeyContainer.isWiped()) {
      throw new Error('Encryption session has been closed');
    }
    const keyString = this.accessKeyContainer.data.toString('utf-8');
    return decryptSeedPhrases(encrypted, keyString);
  }
  
  verify(bundle: SeedPhraseBundle): boolean {
    if (!this.accessKeyContainer || this.accessKeyContainer.isWiped()) {
      throw new Error('Encryption session has been closed');
    }
    const keyString = this.accessKeyContainer.data.toString('utf-8');
    return verifyEncryptionRoundTrip(bundle, keyString);
  }
  
  close(): void {
    if (this.accessKeyContainer) {
      this.accessKeyContainer.wipe();
      this.accessKeyContainer = null;
    }
  }
}
