/**
 * Security utilities test suite
 * 
 * Tests for memory wiping, secure containers, and input validation
 */

import { 
  wipeString, 
  wipeBuffer, 
  SecureContainer,
  validateCardanoAddress,
  validateBitcoinAddress,
  sanitizeError
} from './security';

describe('Memory Wiping', () => {
  describe('wipeBuffer', () => {
    it('should overwrite buffer with zeros', () => {
      const buffer = Buffer.from('sensitive data');
      const originalLength = buffer.length;
      
      wipeBuffer(buffer);
      
      expect(buffer.length).toBe(originalLength);
      expect(buffer.every(byte => byte === 0)).toBe(true);
    });

    it('should handle null buffer gracefully', () => {
      expect(() => wipeBuffer(null as any)).not.toThrow();
    });

    it('should handle non-buffer gracefully', () => {
      expect(() => wipeBuffer('not a buffer' as any)).not.toThrow();
    });
  });

  describe('wipeString - KNOWN VULNERABILITY', () => {
    // This test documents the CRITICAL vulnerability in wipeString
    it('FAILS to wipe string from memory (strings are immutable)', () => {
      const original = 'seed phrase words here';
      let sensitive = original;
      
      wipeString(sensitive);
      
      // ⚠️ THIS WILL FAIL - strings cannot be wiped in JavaScript
      // The original string 'seed phrase words here' remains in memory
      expect(sensitive).toBe(''); // This assertion will pass
      
      // But the original memory still contains the sensitive data
      // This is a CRITICAL security vulnerability
      console.warn('⚠️ SECURITY WARNING: wipeString() is ineffective!');
      console.warn('Seed phrases stored as strings CANNOT be securely wiped');
      console.warn('Use Uint8Array or Buffer instead');
    });
  });
});

describe('SecureContainer', () => {
  describe('with Buffer', () => {
    it('should store and retrieve buffer data', () => {
      const buffer = Buffer.from('secret');
      const container = new SecureContainer(buffer);
      
      expect(container.data).toBe(buffer);
      expect(container.isWiped()).toBe(false);
    });

    it('should wipe buffer data', () => {
      const buffer = Buffer.from('secret');
      const container = new SecureContainer(buffer);
      
      container.wipe();
      
      expect(container.isWiped()).toBe(true);
      expect(buffer.every(byte => byte === 0)).toBe(true);
    });

    it('should throw when accessing wiped data', () => {
      const buffer = Buffer.from('secret');
      const container = new SecureContainer(buffer);
      
      container.wipe();
      
      expect(() => container.data).toThrow('Attempted to access wiped secure data');
    });

    it('should be idempotent when wiping multiple times', () => {
      const buffer = Buffer.from('secret');
      const container = new SecureContainer(buffer);
      
      container.wipe();
      expect(() => container.wipe()).not.toThrow();
      expect(container.isWiped()).toBe(true);
    });
  });

  describe('with string - SECURITY WARNING', () => {
    it('should store string but CANNOT securely wipe it', () => {
      const secret = 'seed phrase words';
      const container = new SecureContainer(secret);
      
      container.wipe();
      
      // Container is marked as wiped
      expect(container.isWiped()).toBe(true);
      
      // But the original string still exists in memory
      console.warn('⚠️ String-based SecureContainer does NOT provide real security');
      console.warn('Use Buffer or Uint8Array for sensitive data');
    });
  });
});

describe('Address Validation', () => {
  describe('validateCardanoAddress', () => {
    it('should accept valid mainnet addresses', () => {
      const validAddresses = [
        'addr1qxyz123456789abcdefghijklmnopqrstuvwxyz123456789abc',
        'addr1q9l5q0qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq',
      ];
      
      validAddresses.forEach(addr => {
        expect(validateCardanoAddress(addr)).toBe(true);
      });
    });

    it('should accept valid testnet addresses', () => {
      const validAddress = 'addr_test1qxyz123456789abcdefghijklmnopqrstuvwxyz123';
      expect(validateCardanoAddress(validAddress)).toBe(true);
    });

    it('should reject invalid addresses', () => {
      const invalidAddresses = [
        'invalid',
        'addr2xyz', // wrong prefix
        'addr1', // too short
        'ADDR1UPPERCASE', // uppercase not allowed
        'addr1_with_underscores',
        'addr1 with spaces',
      ];
      
      invalidAddresses.forEach(addr => {
        expect(validateCardanoAddress(addr)).toBe(false);
      });
    });

    it('should reject empty string', () => {
      expect(validateCardanoAddress('')).toBe(false);
    });
  });

  describe('validateBitcoinAddress', () => {
    it('should accept valid P2PKH addresses', () => {
      const validAddress = '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'; // Genesis block address
      expect(validateBitcoinAddress(validAddress)).toBe(true);
    });

    it('should accept valid P2SH addresses', () => {
      const validAddress = '3J98t1WpEZ73CNmYviecrnyiWrnqRhWNLy';
      expect(validateBitcoinAddress(validAddress)).toBe(true);
    });

    it('should accept valid Bech32 addresses', () => {
      const validAddresses = [
        'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq',
        'tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx', // testnet
      ];
      
      validAddresses.forEach(addr => {
        expect(validateBitcoinAddress(addr)).toBe(true);
      });
    });

    it('should reject invalid addresses', () => {
      const invalidAddresses = [
        'invalid',
        '0InvalidPrefix',
        'bc1', // too short
        'bc1!invalid@chars',
      ];
      
      invalidAddresses.forEach(addr => {
        expect(validateBitcoinAddress(addr)).toBe(false);
      });
    });
  });
});

describe('Error Sanitization', () => {
  it('should redact private keys', () => {
    const error = new Error('Key: abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab');
    const sanitized = sanitizeError(error);
    
    expect(sanitized.message).toContain('[REDACTED_KEY]');
    expect(sanitized.message).not.toContain('abcd1234');
  });

  it('should redact Cardano addresses', () => {
    const error = new Error('Failed to send to addr1qxyz123456789abcdefghijklmnopqrst');
    const sanitized = sanitizeError(error);
    
    expect(sanitized.message).toContain('[REDACTED_ADDRESS]');
    expect(sanitized.message).not.toContain('addr1qxyz');
  });

  it('should redact Bitcoin addresses', () => {
    const error = new Error('Failed at 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa');
    const sanitized = sanitizeError(error);
    
    expect(sanitized.message).toContain('[REDACTED_ADDRESS]');
    expect(sanitized.message).not.toContain('1A1zP1eP');
  });

  it('should redact mnemonic phrases', () => {
    const error = new Error('Mnemonic: abandon ability able about above absent absorb abstract absurd abuse access accident');
    const sanitized = sanitizeError(error);
    
    expect(sanitized.message).toContain('[REDACTED_MNEMONIC]');
    expect(sanitized.message).not.toContain('abandon');
  });

  it('should preserve safe error messages', () => {
    const error = new Error('Invalid amount');
    const sanitized = sanitizeError(error);
    
    expect(sanitized.message).toBe('Invalid amount');
  });

  it('should include error code', () => {
    const error: any = new Error('Test');
    error.code = 'INVALID_INPUT';
    
    const sanitized = sanitizeError(error);
    expect(sanitized.code).toBe('INVALID_INPUT');
  });

  it('should handle errors without message', () => {
    const error = {};
    const sanitized = sanitizeError(error);
    
    expect(sanitized.message).toBe('Unknown error');
    expect(sanitized.code).toBe('UNKNOWN_ERROR');
  });

  // ⚠️ SECURITY TEST: Verify regex doesn't miss edge cases
  describe('Sanitization Edge Cases', () => {
    it('VULNERABILITY: should redact 12-word mnemonics (currently may fail)', () => {
      const error = new Error('abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about');
      const sanitized = sanitizeError(error);
      
      // This test may FAIL due to regex bug in current implementation
      expect(sanitized.message).toContain('[REDACTED_MNEMONIC]');
    });

    it('VULNERABILITY: should handle uppercase addresses', () => {
      const error = new Error('Address: BC1QAR0SRRR7XFKVY5L643LYDNW9RE59GTZZWF5MDQ');
      const sanitized = sanitizeError(error);
      
      // Current implementation may not catch uppercase
      expect(sanitized.message).toContain('[REDACTED');
    });

    it('should handle hex-encoded sensitive data', () => {
      const error = new Error('Key hex: 0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890');
      const sanitized = sanitizeError(error);
      
      expect(sanitized.message).toContain('[REDACTED_KEY]');
    });
  });
});

// Memory leak detection test
describe('Memory Security Integration', () => {
  it('should not leak sensitive data through error stack traces', () => {
    const sensitiveData = 'abandon ability able about above absent absorb abstract';
    
    try {
      throw new Error(`Failed to process: ${sensitiveData}`);
    } catch (error) {
      const sanitized = sanitizeError(error);
      
      // Verify sanitized message doesn't contain mnemonic
      expect(sanitized.message).not.toContain('abandon');
      expect(sanitized.message).toContain('[REDACTED_MNEMONIC]');
      
      // ⚠️ WARNING: Stack trace may still contain sensitive data
      console.warn('⚠️ Stack traces may still leak sensitive data');
      console.warn('Consider implementing stack trace sanitization');
    }
  });
});
