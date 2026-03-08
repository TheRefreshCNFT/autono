/**
 * Access control and rate limiting for access key attempts
 * 
 * Security requirements:
 * - Rate limiting: 3 strikes before locking
 * - Lock duration: 15 minutes after 3 failed attempts
 * - Reset counter after successful access
 */

import { AccessKeyMetadata } from './types';

const MAX_ATTEMPTS = 3;
const LOCK_DURATION_MS = 15 * 60 * 1000; // 15 minutes

/**
 * Access control manager
 */
export class AccessKeyControl {
  private metadata: Map<string, AccessKeyMetadata> = new Map();
  
  /**
   * Initialize metadata for an asset
   */
  private getOrCreateMetadata(assetId: string): AccessKeyMetadata {
    let meta = this.metadata.get(assetId);
    if (!meta) {
      meta = {
        attempts: 0,
        lastAttempt: 0,
        locked: false
      };
      this.metadata.set(assetId, meta);
    }
    return meta;
  }
  
  /**
   * Check if access is allowed
   */
  canAttemptAccess(assetId: string): { allowed: boolean; reason?: string; lockUntil?: number } {
    const meta = this.getOrCreateMetadata(assetId);
    
    // Check if locked
    if (meta.locked && meta.lockUntil) {
      const now = Date.now();
      
      // Check if lock has expired
      if (now >= meta.lockUntil) {
        // Reset after lock expiry
        meta.locked = false;
        meta.attempts = 0;
        meta.lockUntil = undefined;
        this.metadata.set(assetId, meta);
        
        console.log('[INFO] Access lock expired, resetting attempts');
        return { allowed: true };
      } else {
        const remainingMs = meta.lockUntil - now;
        const remainingMin = Math.ceil(remainingMs / 60000);
        
        return {
          allowed: false,
          reason: `Too many failed attempts. Locked for ${remainingMin} more minutes.`,
          lockUntil: meta.lockUntil
        };
      }
    }
    
    return { allowed: true };
  }
  
  /**
   * Record a failed access attempt
   */
  recordFailedAttempt(assetId: string): void {
    const meta = this.getOrCreateMetadata(assetId);
    
    meta.attempts += 1;
    meta.lastAttempt = Date.now();
    
    console.log(`[WARN] Failed access attempt ${meta.attempts}/${MAX_ATTEMPTS} for asset:`, assetId);
    
    // Lock if max attempts reached
    if (meta.attempts >= MAX_ATTEMPTS) {
      meta.locked = true;
      meta.lockUntil = Date.now() + LOCK_DURATION_MS;
      
      console.log('[SECURITY] Asset locked due to too many failed attempts');
      console.log('[SECURITY] Lock duration: 15 minutes');
      console.log('[SECURITY] Lock until:', new Date(meta.lockUntil).toISOString());
    }
    
    this.metadata.set(assetId, meta);
  }
  
  /**
   * Record a successful access
   */
  recordSuccessfulAccess(assetId: string): void {
    const meta = this.getOrCreateMetadata(assetId);
    
    // Reset attempts on success
    meta.attempts = 0;
    meta.lastAttempt = Date.now();
    meta.locked = false;
    meta.lockUntil = undefined;
    
    console.log('[INFO] Successful access recorded, attempts reset');
    
    this.metadata.set(assetId, meta);
  }
  
  /**
   * Get current metadata for an asset
   */
  getMetadata(assetId: string): AccessKeyMetadata {
    return this.getOrCreateMetadata(assetId);
  }
  
  /**
   * Manually reset attempts (admin function)
   */
  resetAttempts(assetId: string): void {
    const meta = this.getOrCreateMetadata(assetId);
    
    meta.attempts = 0;
    meta.locked = false;
    meta.lockUntil = undefined;
    
    console.log('[INFO] Access attempts manually reset for asset:', assetId);
    
    this.metadata.set(assetId, meta);
  }
  
  /**
   * Get remaining attempts before lock
   */
  getRemainingAttempts(assetId: string): number {
    const meta = this.getOrCreateMetadata(assetId);
    return Math.max(0, MAX_ATTEMPTS - meta.attempts);
  }
  
  /**
   * Check if asset is locked
   */
  isLocked(assetId: string): boolean {
    const meta = this.getOrCreateMetadata(assetId);
    
    if (!meta.locked) return false;
    
    // Check if lock has expired
    if (meta.lockUntil && Date.now() >= meta.lockUntil) {
      this.resetAttempts(assetId);
      return false;
    }
    
    return true;
  }
  
  /**
   * Get lock expiry time
   */
  getLockExpiry(assetId: string): Date | null {
    const meta = this.getOrCreateMetadata(assetId);
    
    if (!meta.locked || !meta.lockUntil) return null;
    
    return new Date(meta.lockUntil);
  }
  
  /**
   * Clear all metadata (use with caution)
   */
  clearAll(): void {
    this.metadata.clear();
    console.log('[INFO] All access control metadata cleared');
  }
  
  /**
   * Get statistics
   */
  getStats(): {
    totalAssets: number;
    lockedAssets: number;
    assetsWithFailures: number;
  } {
    let lockedCount = 0;
    let failureCount = 0;
    
    const entries = Array.from(this.metadata.entries());
    for (const [_, meta] of entries) {
      if (meta.locked) lockedCount++;
      if (meta.attempts > 0) failureCount++;
    }
    
    return {
      totalAssets: this.metadata.size,
      lockedAssets: lockedCount,
      assetsWithFailures: failureCount
    };
  }
}

/**
 * Global access control instance
 */
export const globalAccessControl = new AccessKeyControl();
