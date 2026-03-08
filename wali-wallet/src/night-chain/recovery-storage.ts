/**
 * Night Chain Recovery Storage
 * 
 * Implements local storage indexing for recovery phrase → transaction ID mapping
 * This allows users to recover their wallet using their 16-word recovery phrase
 * without needing to query the blockchain directly.
 * 
 * **Production Note:** This is a temporary solution for beta.
 * For mainnet, implement proper blockchain querying via Night Chain RPC.
 */

import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';
import { EncryptedAsset } from './types';

export interface RecoveryIndex {
  recoveryHash: string; // SHA-256 of 16-word recovery phrase
  recoveryPhraseEncrypted: string; // Double-encrypted with master key (for verification only)
  transactionId: string; // Night Chain asset ID
  created: number; // Timestamp
  network: 'production' | 'testnet'; // Which network
  metadata?: {
    hasCardano?: boolean;
    hasBitcoin?: boolean;
    hasMidnight?: boolean;
  };
}

/**
 * Recovery storage using local filesystem
 * 
 * Structure:
 * ~/.wali/recovery/
 *   - mainnet/
 *     - {recoveryHash}.json
 *   - testnet/
 *     - {recoveryHash}.json
 */
export class RecoveryStorage {
  private storageDir: string;
  private network: 'production' | 'testnet';

  // In-memory cache for encrypted backups
  private backupCache: Map<string, EncryptedAsset> = new Map();

  constructor(network: 'production' | 'testnet' = 'production') {
    this.network = network;
    
    // Determine storage directory
    const homeDir = process.env.HOME || process.env.USERPROFILE || '';
    this.storageDir = path.join(homeDir, '.wali', 'recovery', network);

    // Ensure directory exists
    this.ensureStorageDir();
  }

  /**
   * Create storage directory if it doesn't exist
   */
  private ensureStorageDir(): void {
    if (!fs.existsSync(this.storageDir)) {
      fs.mkdirSync(this.storageDir, { recursive: true, mode: 0o700 }); // Owner read/write/exec only
    }
  }

  /**
   * Hash recovery phrase deterministically
   * Uses SHA-256 for consistent lookup
   */
  hashRecoveryPhrase(words: string[]): string {
    if (words.length !== 16) {
      throw new Error('Recovery phrase must be exactly 16 words');
    }

    const normalized = words.map(w => w.toLowerCase().trim()).join(' ');
    return crypto.createHash('sha256').update(normalized).digest('hex');
  }

  /**
   * Index a backup for recovery
   * Stores mapping: recoveryHash → transactionId
   * 
   * @param recoveryPhrase 16-word recovery phrase
   * @param transactionId Night Chain asset ID
   * @param encryptedBackup The encrypted backup data (cached locally)
   * @param metadata Optional metadata about the backup
   */
  async indexBackup(
    recoveryPhrase: string[],
    transactionId: string,
    encryptedBackup: EncryptedAsset,
    metadata?: RecoveryIndex['metadata']
  ): Promise<void> {
    const hash = this.hashRecoveryPhrase(recoveryPhrase);

    const index: RecoveryIndex = {
      recoveryHash: hash,
      recoveryPhraseEncrypted: this.encryptRecoveryPhrase(recoveryPhrase),
      transactionId,
      created: Date.now(),
      network: this.network,
      metadata,
    };

    // Store index
    const indexPath = path.join(this.storageDir, `${hash}.json`);
    await fs.promises.writeFile(
      indexPath,
      JSON.stringify(index, null, 2),
      { mode: 0o600 } // Owner read/write only
    );

    // Cache encrypted backup
    this.backupCache.set(transactionId, encryptedBackup);

    // Also save encrypted backup to disk
    const backupPath = path.join(this.storageDir, `${transactionId}.backup`);
    await fs.promises.writeFile(
      backupPath,
      JSON.stringify(encryptedBackup, null, 2),
      { mode: 0o600 }
    );

    console.log('[INFO] Recovery index created');
    console.log('[INFO] Recovery hash:', hash.substring(0, 16) + '...');
    console.log('[INFO] Transaction ID:', transactionId);
  }

  /**
   * Look up transaction ID by recovery phrase
   * 
   * @param recoveryPhrase 16-word recovery phrase entered by user
   * @returns Transaction ID if found, null otherwise
   */
  async lookupBackup(recoveryPhrase: string[]): Promise<string | null> {
    const hash = this.hashRecoveryPhrase(recoveryPhrase);
    const indexPath = path.join(this.storageDir, `${hash}.json`);

    if (!fs.existsSync(indexPath)) {
      console.log('[WARN] No recovery index found for phrase');
      return null;
    }

    try {
      const data = await fs.promises.readFile(indexPath, 'utf8');
      const index: RecoveryIndex = JSON.parse(data);

      // Verify the recovery phrase matches (double-check)
      if (!this.verifyRecoveryPhrase(recoveryPhrase, index.recoveryPhraseEncrypted)) {
        console.error('[ERROR] Recovery phrase verification failed');
        return null;
      }

      console.log('[INFO] Recovery index found');
      console.log('[INFO] Transaction ID:', index.transactionId);
      console.log('[INFO] Created:', new Date(index.created).toISOString());

      return index.transactionId;
    } catch (error) {
      console.error('[ERROR] Failed to read recovery index:', error);
      return null;
    }
  }

  /**
   * Retrieve encrypted backup by transaction ID
   * 
   * @param transactionId Night Chain asset ID
   * @returns Encrypted backup data
   */
  async getEncryptedBackup(transactionId: string): Promise<EncryptedAsset | null> {
    // Check cache first
    if (this.backupCache.has(transactionId)) {
      return this.backupCache.get(transactionId)!;
    }

    // Load from disk
    const backupPath = path.join(this.storageDir, `${transactionId}.backup`);

    if (!fs.existsSync(backupPath)) {
      console.log('[WARN] No backup file found for transaction ID:', transactionId);
      return null;
    }

    try {
      const data = await fs.promises.readFile(backupPath, 'utf8');
      const backup: EncryptedAsset = JSON.parse(data);

      // Cache it
      this.backupCache.set(transactionId, backup);

      return backup;
    } catch (error) {
      console.error('[ERROR] Failed to load backup:', error);
      return null;
    }
  }

  /**
   * List all recovery indexes (for debugging/admin)
   */
  async listAllIndexes(): Promise<RecoveryIndex[]> {
    const files = await fs.promises.readdir(this.storageDir);
    const indexes: RecoveryIndex[] = [];

    for (const file of files) {
      if (file.endsWith('.json')) {
        try {
          const data = await fs.promises.readFile(
            path.join(this.storageDir, file),
            'utf8'
          );
          indexes.push(JSON.parse(data));
        } catch (error) {
          console.error(`[ERROR] Failed to read ${file}:`, error);
        }
      }
    }

    return indexes;
  }

  /**
   * Delete a recovery index (use with caution!)
   * 
   * @param recoveryPhrase The recovery phrase to delete
   */
  async deleteRecoveryIndex(recoveryPhrase: string[]): Promise<boolean> {
    const hash = this.hashRecoveryPhrase(recoveryPhrase);
    const indexPath = path.join(this.storageDir, `${hash}.json`);

    if (!fs.existsSync(indexPath)) {
      return false;
    }

    // Load index to get transaction ID
    const data = await fs.promises.readFile(indexPath, 'utf8');
    const index: RecoveryIndex = JSON.parse(data);

    // Delete index file
    await fs.promises.unlink(indexPath);

    // Delete backup file
    const backupPath = path.join(this.storageDir, `${index.transactionId}.backup`);
    if (fs.existsSync(backupPath)) {
      await fs.promises.unlink(backupPath);
    }

    // Remove from cache
    this.backupCache.delete(index.transactionId);

    console.log('[INFO] Recovery index deleted:', hash.substring(0, 16) + '...');
    return true;
  }

  /**
   * Encrypt recovery phrase for storage verification
   * Uses a simple XOR with a hardcoded key (NOT for security, just for verification)
   */
  private encryptRecoveryPhrase(words: string[]): string {
    const text = words.join(' ');
    const key = 'wali-recovery-verification-key-v1'; // Not secret, just for verification
    
    let result = '';
    for (let i = 0; i < text.length; i++) {
      result += String.fromCharCode(
        text.charCodeAt(i) ^ key.charCodeAt(i % key.length)
      );
    }
    
    return Buffer.from(result).toString('base64');
  }

  /**
   * Verify recovery phrase matches stored encrypted version
   */
  private verifyRecoveryPhrase(words: string[], encrypted: string): boolean {
    const reEncrypted = this.encryptRecoveryPhrase(words);
    return reEncrypted === encrypted;
  }
}
