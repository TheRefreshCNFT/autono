/**
 * Security utilities for handling sensitive data
 */

/**
 * Securely wipe a Uint8Array from memory
 * Uses multiple passes with random data followed by zeros (DOD 5220.22-M standard)
 */
export function wipeMemory(data: Uint8Array): void {
  if (!data || data.length === 0) return;
  
  // Pass 1: Fill with random data
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    crypto.getRandomValues(data as any);
  } else {
    // Fallback for Node.js without crypto global
    const nodeCrypto = require('crypto');
    nodeCrypto.randomFillSync(data);
  }
  
  // Pass 2: Fill with zeros
  data.fill(0);
  
  // Pass 3: Fill with random data again
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    crypto.getRandomValues(data as any);
  } else {
    const nodeCrypto = require('crypto');
    nodeCrypto.randomFillSync(data);
  }
  
  // Final pass: Fill with zeros
  data.fill(0);
}

/**
 * Securely wipe a Buffer from memory
 */
export function wipeBuffer(buffer: Buffer): void {
  if (!buffer || !Buffer.isBuffer(buffer)) return;
  
  // Convert to Uint8Array view and wipe
  const view = new Uint8Array(buffer.buffer, buffer.byteOffset, buffer.byteLength);
  wipeMemory(view);
}

/**
 * Securely wipe a string from memory
 * Note: JavaScript strings are immutable, but we can try to overwrite the underlying buffer
 * This is best-effort - for truly sensitive data, use SecureContainer with Uint8Array/Buffer
 */
export function wipeString(str: string): void {
  if (!str || typeof str !== 'string') return;
  
  // Strings are immutable in JS, so we can't actually wipe them
  // The best we can do is convert to a buffer and wipe that
  // This is why SecureContainer should be used for sensitive data
  
  // Create a buffer representation and wipe it
  const buffer = Buffer.from(str, 'utf-8');
  wipeBuffer(buffer);
  
  // Note: The original string reference may still exist in memory
  // until garbage collection. This is a limitation of JavaScript.
}

/**
 * Create a secure container for sensitive data that auto-wipes
 * Now handles Uint8Array instead of string for better security
 */
export class SecureContainer<T extends Uint8Array | Buffer> {
  private _data: T | null;
  private _wiped: boolean = false;

  constructor(data: T) {
    this._data = data;
  }

  get data(): T {
    if (this._wiped) {
      throw new Error('Attempted to access wiped secure data');
    }
    if (!this._data) {
      throw new Error('No data in secure container');
    }
    return this._data;
  }

  wipe(): void {
    if (this._wiped) return;

    if (this._data) {
      if (this._data instanceof Uint8Array) {
        wipeMemory(this._data);
      } else if (Buffer.isBuffer(this._data)) {
        wipeBuffer(this._data);
      }
      this._data = null;
    }
    this._wiped = true;
  }

  isWiped(): boolean {
    return this._wiped;
  }
}

/**
 * Validate address format (basic sanity check)
 */
export function validateCardanoAddress(address: string): boolean {
  // Cardano addresses start with addr1 (mainnet) or addr_test1 (testnet)
  return /^(addr1|addr_test1)[a-z0-9]{50,}$/.test(address);
}

/**
 * Validate Bitcoin address format
 */
export function validateBitcoinAddress(address: string): boolean {
  // Basic check for common Bitcoin address formats
  // P2PKH: starts with 1
  // P2SH: starts with 3
  // Bech32: starts with bc1 (mainnet) or tb1 (testnet)
  return /^(1|3|bc1|tb1)[a-zA-Z0-9]{25,62}$/.test(address);
}

/**
 * Sanitize error messages to prevent sensitive data leakage
 * FIXED: Improved regex patterns to properly catch mnemonics, private keys, and addresses
 */
export function sanitizeError(error: any): { code: string; message: string; details?: any } {
  const message = error.message || 'Unknown error';
  
  // Remove potential sensitive data patterns
  const sanitized = message
    // Private keys: 64 hex characters (more precise pattern)
    .replace(/\b[a-fA-F0-9]{64}\b/g, '[REDACTED_PRIVATE_KEY]')
    // Mnemonics: 12-24 word sequences (fixed to properly catch all lengths)
    .replace(/\b([a-z]{3,8}\s+){11}[a-z]{3,8}\b/gi, '[REDACTED_MNEMONIC]') // 12 words
    .replace(/\b([a-z]{3,8}\s+){14}[a-z]{3,8}\b/gi, '[REDACTED_MNEMONIC]') // 15 words
    .replace(/\b([a-z]{3,8}\s+){17}[a-z]{3,8}\b/gi, '[REDACTED_MNEMONIC]') // 18 words
    .replace(/\b([a-z]{3,8}\s+){20}[a-z]{3,8}\b/gi, '[REDACTED_MNEMONIC]') // 21 words
    .replace(/\b([a-z]{3,8}\s+){23}[a-z]{3,8}\b/gi, '[REDACTED_MNEMONIC]') // 24 words
    // Cardano addresses
    .replace(/\b(addr1|addr_test1)[a-z0-9]+\b/g, '[REDACTED_CARDANO_ADDRESS]')
    // Bitcoin addresses (P2PKH, P2SH)
    .replace(/\b[13][a-km-zA-HJ-NP-Z1-9]{25,62}\b/g, '[REDACTED_BITCOIN_ADDRESS]')
    // Bitcoin addresses (Bech32)
    .replace(/\b(bc1|tb1)[a-zA-HJ-NP-Z0-9]{25,62}\b/g, '[REDACTED_BITCOIN_ADDRESS]')
    // Hex-encoded data (potential keys/seeds)
    .replace(/\b0x[a-fA-F0-9]{32,}\b/g, '[REDACTED_HEX_DATA]')
    // Base64-encoded data (potential keys/seeds) - at least 32 chars
    .replace(/\b[A-Za-z0-9+/]{32,}={0,2}\b/g, '[REDACTED_BASE64_DATA]');

  return {
    code: error.code || 'UNKNOWN_ERROR',
    message: sanitized,
    details: error.details
  };
}
