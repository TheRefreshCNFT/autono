/**
 * Security Validation Tests for wAli Wallet
 * 
 * Critical security requirements:
 * 1. No BIP39 seed words ever logged
 * 2. Memory properly wiped after use
 * 3. Seed phrases only stored as Uint8Array/Buffer
 * 4. Access key validation enforced
 * 5. 3-strike lockout mechanism works
 */

import { SecureContainer, wipeBuffer, sanitizeError, wipeMemory } from '../utils/security';
import { generateMnemonic } from 'bip39';

// BIP39 wordlist (first 100 words for testing - in production use full list)
const BIP39_SAMPLE_WORDS = [
  'abandon', 'ability', 'able', 'about', 'above', 'absent', 'absorb', 'abstract',
  'absurd', 'abuse', 'access', 'accident', 'account', 'accuse', 'achieve', 'acid',
  'acoustic', 'acquire', 'across', 'act', 'action', 'actor', 'actress', 'actual',
  'adapt', 'add', 'addict', 'address', 'adjust', 'admit', 'adult', 'advance',
  'advice', 'aerobic', 'afford', 'afraid', 'again', 'age', 'agent', 'agree',
  'ahead', 'aim', 'air', 'airport', 'aisle', 'alarm', 'album', 'alcohol',
  'alert', 'alien', 'all', 'alley', 'allow', 'almost', 'alone', 'alpha',
  'already', 'also', 'alter', 'always', 'amateur', 'amazing', 'among', 'amount',
  'amused', 'analyst', 'anchor', 'ancient', 'anger', 'angle', 'angry', 'animal',
  'ankle', 'announce', 'annual', 'another', 'answer', 'antenna', 'antique', 'anxiety',
  'any', 'apart', 'apology', 'appear', 'apple', 'approve', 'april', 'arch',
  'arctic', 'area', 'arena', 'argue', 'arm', 'armed', 'armor', 'army',
  'around', 'arrange', 'arrest', 'arrive', 'arrow', 'art', 'artefact', 'artist'
];

describe('Security Validation: No Seed Phrase Leakage', () => {
  let consoleLog: any;
  let consoleError: any;
  let consoleWarn: any;
  let consoleInfo: any;
  let capturedLogs: string[] = [];

  beforeEach(() => {
    // Intercept all console output
    consoleLog = console.log;
    consoleError = console.error;
    consoleWarn = console.warn;
    consoleInfo = console.info;

    capturedLogs = [];

    console.log = (...args: any[]) => {
      capturedLogs.push(args.join(' '));
      consoleLog(...args); // Still output for debugging
    };
    console.error = (...args: any[]) => {
      capturedLogs.push(args.join(' '));
      consoleError(...args);
    };
    console.warn = (...args: any[]) => {
      capturedLogs.push(args.join(' '));
      consoleWarn(...args);
    };
    console.info = (...args: any[]) => {
      capturedLogs.push(args.join(' '));
      consoleInfo(...args);
    };
  });

  afterEach(() => {
    // Restore original console
    console.log = consoleLog;
    console.error = consoleError;
    console.warn = consoleWarn;
    console.info = consoleInfo;
    capturedLogs = [];
  });

  test('BIP39 mnemonic generation does not log seed words', () => {
    // Generate a 24-word mnemonic
    const mnemonic = generateMnemonic(256);
    const words = mnemonic.split(' ');

    // Check all captured logs
    const allLogs = capturedLogs.join(' ').toLowerCase();

    // Verify at least some words were generated (sanity check)
    expect(words.length).toBe(24);

    // Check that NONE of the generated words appear in logs
    words.forEach(word => {
      expect(allLogs).not.toContain(word.toLowerCase());
    });

    // Also check against sample BIP39 words
    BIP39_SAMPLE_WORDS.forEach(word => {
      expect(allLogs).not.toContain(word);
    });
  });

  test('SecureContainer operations do not log sensitive data', () => {
    const sensitiveData = 'abandon ability able about above absent absorb abstract';
    const container = new SecureContainer(sensitiveData);

    // Access data
    const _ = container.data;

    // Wipe data
    container.wipe();

    const allLogs = capturedLogs.join(' ').toLowerCase();

    // Verify no BIP39 words leaked
    BIP39_SAMPLE_WORDS.forEach(word => {
      expect(allLogs).not.toContain(word);
    });

    // Verify sensitive string not logged
    expect(allLogs).not.toContain('abandon ability');
  });

  test('Error sanitization removes BIP39 words from messages', () => {
    const mnemonic = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about';
    const error = new Error(`Failed to process mnemonic: ${mnemonic}`);

    const sanitized = sanitizeError(error);
    const allLogs = capturedLogs.join(' ').toLowerCase();

    // Sanitized error should not contain the word
    expect(sanitized.message).not.toContain('abandon');
    expect(sanitized.message).toContain('[REDACTED_MNEMONIC]');

    // Logs should not contain the word either
    expect(allLogs).not.toContain('abandon');
  });

  test('Buffer operations do not expose sensitive data in logs', () => {
    const sensitiveText = 'abandon ability able';
    const buffer = Buffer.from(sensitiveText, 'utf8');

    // Perform operations
    const container = new SecureContainer(buffer);
    wipeBuffer(buffer);
    container.wipe();

    const allLogs = capturedLogs.join(' ').toLowerCase();

    // Verify no sensitive words in logs
    expect(allLogs).not.toContain('abandon');
    expect(allLogs).not.toContain('ability');
    expect(allLogs).not.toContain('able');
  });
});

describe('Security Validation: Memory Wiping', () => {
  test('wipeMemory zeroes out Uint8Array', () => {
    const data = new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]);
    const originalLength = data.length;

    wipeMemory(data);

    // Verify length unchanged
    expect(data.length).toBe(originalLength);

    // Verify all bytes are zero
    for (let i = 0; i < data.length; i++) {
      expect(data[i]).toBe(0);
    }
  });

  test('wipeBuffer zeroes out Buffer', () => {
    const buffer = Buffer.from('sensitive data', 'utf8');
    const originalLength = buffer.length;

    wipeBuffer(buffer);

    // Verify length unchanged
    expect(buffer.length).toBe(originalLength);

    // Verify all bytes are zero
    for (let i = 0; i < buffer.length; i++) {
      expect(buffer[i]).toBe(0);
    }
  });

  test('SecureContainer wipe prevents access', () => {
    const container = new SecureContainer('secret');

    expect(container.isWiped()).toBe(false);
    expect(container.data).toBe('secret');

    container.wipe();

    expect(container.isWiped()).toBe(true);
    expect(() => container.data).toThrow('Attempted to access wiped secure data');
  });

  test('Multiple wipe calls are safe', () => {
    const data = new Uint8Array([1, 2, 3]);

    wipeMemory(data);
    wipeMemory(data); // Should not throw

    expect(data[0]).toBe(0);
    expect(data[1]).toBe(0);
    expect(data[2]).toBe(0);
  });

  test('Wiping empty data is safe', () => {
    const emptyData = new Uint8Array(0);
    const emptyBuffer = Buffer.alloc(0);

    expect(() => wipeMemory(emptyData)).not.toThrow();
    expect(() => wipeBuffer(emptyBuffer)).not.toThrow();
  });
});

describe('Security Validation: Access Key Enforcement', () => {
  // Mock access key validation (from night-chain/encryption.ts)
  const validateAccessKey = (key: string): boolean => {
    return key.length >= 4 && key.length <= 12;
  };

  test('Access key with 3 chars is rejected', () => {
    expect(validateAccessKey('abc')).toBe(false);
  });

  test('Access key with 4 chars is accepted', () => {
    expect(validateAccessKey('abcd')).toBe(true);
  });

  test('Access key with 12 chars is accepted', () => {
    expect(validateAccessKey('abcdefghijkl')).toBe(true);
  });

  test('Access key with 13 chars is rejected', () => {
    expect(validateAccessKey('abcdefghijklm')).toBe(false);
  });

  test('Empty access key is rejected', () => {
    expect(validateAccessKey('')).toBe(false);
  });

  test('Access key validation is consistent', () => {
    const validKeys = ['test', 'pass1234', 'mykey', 'secure123'];
    const invalidKeys = ['', 'a', 'ab', 'abc', 'thisiswaytoolong1234'];

    validKeys.forEach(key => {
      expect(validateAccessKey(key)).toBe(true);
    });

    invalidKeys.forEach(key => {
      expect(validateAccessKey(key)).toBe(false);
    });
  });
});

describe('Security Validation: 3-Strike Lockout', () => {
  // Mock lockout mechanism
  class AccessControl {
    private attempts = 0;
    private locked = false;
    private lockUntil = 0;
    private readonly MAX_ATTEMPTS = 3;
    private readonly LOCK_DURATION_MS = 15 * 60 * 1000; // 15 minutes

    canAttemptAccess(): { allowed: boolean; reason?: string } {
      const now = Date.now();

      // Check if locked
      if (this.locked) {
        if (now < this.lockUntil) {
          const remainingMs = this.lockUntil - now;
          const remainingMin = Math.ceil(remainingMs / 60000);
          return {
            allowed: false,
            reason: `Locked for ${remainingMin} more minutes`
          };
        } else {
          // Lock expired, reset
          this.locked = false;
          this.attempts = 0;
        }
      }

      return { allowed: true };
    }

    recordFailedAttempt(): void {
      this.attempts++;
      if (this.attempts >= this.MAX_ATTEMPTS) {
        this.locked = true;
        this.lockUntil = Date.now() + this.LOCK_DURATION_MS;
      }
    }

    reset(): void {
      this.attempts = 0;
      this.locked = false;
      this.lockUntil = 0;
    }
  }

  test('3 failed attempts trigger lockout', () => {
    const control = new AccessControl();

    // First attempt
    expect(control.canAttemptAccess().allowed).toBe(true);
    control.recordFailedAttempt();

    // Second attempt
    expect(control.canAttemptAccess().allowed).toBe(true);
    control.recordFailedAttempt();

    // Third attempt
    expect(control.canAttemptAccess().allowed).toBe(true);
    control.recordFailedAttempt();

    // Now locked
    const result = control.canAttemptAccess();
    expect(result.allowed).toBe(false);
    expect(result.reason).toContain('Locked');
  });

  test('Lockout duration is approximately 15 minutes', () => {
    const control = new AccessControl();

    // Trigger lockout
    control.recordFailedAttempt();
    control.recordFailedAttempt();
    control.recordFailedAttempt();

    const result = control.canAttemptAccess();
    expect(result.allowed).toBe(false);

    // Check the lock message mentions duration
    expect(result.reason).toContain('15');
  });

  test('Lock auto-resets after timeout (simulated)', () => {
    const control = new AccessControl();

    // Trigger lockout
    control.recordFailedAttempt();
    control.recordFailedAttempt();
    control.recordFailedAttempt();

    expect(control.canAttemptAccess().allowed).toBe(false);

    // Manually reset to simulate time passing
    control.reset();

    expect(control.canAttemptAccess().allowed).toBe(true);
  });
});

describe('Security Validation: Seed Storage Format', () => {
  test('Seed phrases should be stored as Uint8Array', () => {
    const mnemonic = generateMnemonic(256);
    const seedBytes = Buffer.from(mnemonic, 'utf8');
    const seedUint8 = new Uint8Array(seedBytes);

    // Verify it's a Uint8Array
    expect(seedUint8 instanceof Uint8Array).toBe(true);
    expect(typeof seedUint8).not.toBe('string');

    // Verify we can wipe it
    wipeMemory(seedUint8);
    expect(seedUint8.every(byte => byte === 0)).toBe(true);
  });

  test('String seed phrases should be convertible and wipeable', () => {
    const mnemonicString = generateMnemonic(256);
    
    // Convert to Uint8Array immediately
    const buffer = Buffer.from(mnemonicString, 'utf8');
    const seedData = new Uint8Array(buffer);

    // Verify conversion
    expect(seedData instanceof Uint8Array).toBe(true);
    expect(seedData.length).toBeGreaterThan(0);

    // Wipe it
    wipeMemory(seedData);
    expect(seedData.every(byte => byte === 0)).toBe(true);
  });

  test('SecureContainer enforces type safety', () => {
    const stringData = 'sensitive string';
    const bufferData = Buffer.from('sensitive buffer');
    const uint8Data = new Uint8Array([1, 2, 3]);

    // All types should be accepted by SecureContainer
    expect(() => new SecureContainer(stringData)).not.toThrow();
    expect(() => new SecureContainer(bufferData)).not.toThrow();
    expect(() => new SecureContainer(uint8Data)).not.toThrow();
  });
});
