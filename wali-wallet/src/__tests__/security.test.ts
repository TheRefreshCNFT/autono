/**
 * Security utilities tests
 */

import { SecureContainer, wipeBuffer, sanitizeError } from '../utils/security';

describe('Security Utilities', () => {
  describe('SecureContainer', () => {
    test('should store and retrieve data', () => {
      const testData = 'sensitive data';
      const container = new SecureContainer(testData);

      expect(container.data).toBe(testData);
      expect(container.isWiped()).toBe(false);
    });

    test('should wipe string data', () => {
      const container = new SecureContainer('sensitive data');
      
      container.wipe();
      
      expect(container.isWiped()).toBe(true);
      expect(() => container.data).toThrow('Attempted to access wiped secure data');
    });

    test('should wipe buffer data', () => {
      const buffer = Buffer.from('sensitive data');
      const container = new SecureContainer(buffer);
      
      container.wipe();
      
      expect(container.isWiped()).toBe(true);
      expect(() => container.data).toThrow('Attempted to access wiped secure data');
    });

    test('should handle multiple wipe calls safely', () => {
      const container = new SecureContainer('data');
      
      container.wipe();
      container.wipe(); // Should not throw
      
      expect(container.isWiped()).toBe(true);
    });
  });

  describe('wipeBuffer', () => {
    test('should overwrite buffer with zeros', () => {
      const buffer = Buffer.from('sensitive data');
      const originalLength = buffer.length;
      
      wipeBuffer(buffer);
      
      expect(buffer.length).toBe(originalLength);
      expect(buffer.every(byte => byte === 0)).toBe(true);
    });

    test('should handle null buffer safely', () => {
      expect(() => wipeBuffer(null as any)).not.toThrow();
    });
  });

  describe('sanitizeError', () => {
    test('should redact private keys from error messages', () => {
      const error = new Error('Key: a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd');
      const sanitized = sanitizeError(error);

      expect(sanitized.message).toContain('[REDACTED_KEY]');
      expect(sanitized.message).not.toMatch(/[a-f0-9]{64}/);
    });

    test('should redact Cardano addresses from error messages', () => {
      const error = new Error('Invalid address: addr1qxyz123456789abcdefghijklmnopqrstuvwxyz123');
      const sanitized = sanitizeError(error);

      expect(sanitized.message).toContain('[REDACTED_ADDRESS]');
      expect(sanitized.message).not.toContain('addr1');
    });

    test('should redact Bitcoin addresses from error messages', () => {
      const error = new Error('Failed to send to: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa');
      const sanitized = sanitizeError(error);

      expect(sanitized.message).toContain('[REDACTED_ADDRESS]');
      expect(sanitized.message).not.toContain('1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa');
    });

    test('should redact mnemonics from error messages', () => {
      const error = new Error('Invalid mnemonic: abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about');
      const sanitized = sanitizeError(error);

      expect(sanitized.message).toContain('[REDACTED_MNEMONIC]');
      expect(sanitized.message).not.toContain('abandon');
    });

    test('should handle errors without messages', () => {
      const error = {};
      const sanitized = sanitizeError(error);

      expect(sanitized.message).toBe('Unknown error');
      expect(sanitized.code).toBe('UNKNOWN_ERROR');
    });

    test('should preserve error codes', () => {
      const error = { code: 'CUSTOM_ERROR', message: 'Test error' };
      const sanitized = sanitizeError(error);

      expect(sanitized.code).toBe('CUSTOM_ERROR');
    });
  });
});
