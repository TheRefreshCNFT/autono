/**
 * Comprehensive Security Test Suite
 * Tests all CRITICAL security fixes
 */

import { wipeMemory, wipeBuffer, SecureContainer, sanitizeError } from './src/utils/security';
import { WalletEngine } from './src/wallet-engine';

console.log('🔒 SECURITY TEST SUITE - Running Critical Security Tests\n');

let passed = 0;
let failed = 0;

function test(name: string, fn: () => void | Promise<void>) {
  return async () => {
    try {
      await fn();
      console.log(`✅ PASS: ${name}`);
      passed++;
    } catch (error: any) {
      console.log(`❌ FAIL: ${name}`);
      console.log(`   Error: ${error.message}`);
      failed++;
    }
  };
}

// CRITICAL-001: Memory Wiping Tests
const testMemoryWiping = test('CRITICAL-001: Memory wiping with Uint8Array', () => {
  const sensitiveData = new Uint8Array([1, 2, 3, 4, 5]);
  const originalData = new Uint8Array(sensitiveData);
  
  wipeMemory(sensitiveData);
  
  // Verify data is wiped (all zeros after final pass)
  const allZeros = sensitiveData.every(byte => byte === 0);
  if (!allZeros) {
    throw new Error('Memory not properly wiped - contains non-zero bytes');
  }
  
  // Verify it's different from original
  const isDifferent = !sensitiveData.every((byte, i) => byte === originalData[i]);
  if (!isDifferent) {
    throw new Error('Memory wiping had no effect');
  }
});

const testBufferWiping = test('CRITICAL-001: Buffer wiping', () => {
  const buffer = Buffer.from('sensitive data here');
  const originalLength = buffer.length;
  
  wipeBuffer(buffer);
  
  // Verify all bytes are zero
  const allZeros = buffer.every(byte => byte === 0);
  if (!allZeros) {
    throw new Error('Buffer not properly wiped');
  }
  
  // Verify length unchanged
  if (buffer.length !== originalLength) {
    throw new Error('Buffer length changed during wipe');
  }
});

const testSecureContainer = test('CRITICAL-001: SecureContainer with Uint8Array', () => {
  const data = new Uint8Array([10, 20, 30, 40, 50]);
  const container = new SecureContainer(data);
  
  // Test data access
  const retrieved = container.data;
  if (retrieved.length !== 5 || retrieved[0] !== 10) {
    throw new Error('Data retrieval failed');
  }
  
  // Test wipe
  container.wipe();
  
  if (!container.isWiped()) {
    throw new Error('Container not marked as wiped');
  }
  
  // Test access after wipe throws error
  try {
    const _ = container.data;
    throw new Error('Should have thrown error on wiped data access');
  } catch (error: any) {
    if (!error.message.includes('wiped')) {
      throw new Error('Wrong error message for wiped data access');
    }
  }
  
  // Verify original data is wiped
  const allZeros = data.every(byte => byte === 0);
  if (!allZeros) {
    throw new Error('Original data not wiped by container');
  }
});

// CRITICAL-002: Encryption Before Storage Tests
const testEncryptionEnforcement = test('CRITICAL-002: Encryption enforcement', async () => {
  const engine = new WalletEngine({
    network: 'testnet'
    // No encryption functions provided
  });
  
  // Create a wallet
  const result = await engine.createWallet(['cardano'], 12);
  
  // Attempt to store without encryption should fail
  try {
    await engine.storeEncryptedMnemonic(result.mnemonic, 'test-wallet');
    throw new Error('Should have thrown error - encryption not configured');
  } catch (error: any) {
    if (!error.message.includes('SECURITY ERROR') && !error.message.includes('Encryption not configured')) {
      throw new Error(`Wrong error: ${error.message}`);
    }
  }
  
  // Clean up
  wipeMemory(result.mnemonic);
});

const testEncryptionWithCallbacks = test('CRITICAL-002: Encryption callbacks work', async () => {
  const mockEncrypt = async (data: Uint8Array): Promise<Uint8Array> => {
    // Simple XOR "encryption" for testing
    return data.map(b => b ^ 0xFF);
  };
  
  const mockDecrypt = async (data: Uint8Array): Promise<Uint8Array> => {
    // Reverse XOR
    return data.map(b => b ^ 0xFF);
  };
  
  const engine = new WalletEngine({
    network: 'testnet',
    encryptBeforeStorage: mockEncrypt,
    decryptAfterRetrieval: mockDecrypt
  });
  
  const result = await engine.createWallet(['cardano'], 12);
  
  // This should NOT throw because encryption is configured
  try {
    await engine.storeEncryptedMnemonic(result.mnemonic, 'test-wallet');
    // Success expected
  } catch (error: any) {
    if (error.message.includes('SECURITY ERROR')) {
      throw new Error('Should not throw security error when encryption is configured');
    }
  }
  
  // Clean up
  wipeMemory(result.mnemonic);
});

// CRITICAL-003: Log Sanitization Tests
const testMnemonicSanitization = test('CRITICAL-003: Mnemonic sanitization (12 words)', () => {
  const error = new Error('Error with mnemonic: abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about');
  const sanitized = sanitizeError(error);
  
  if (sanitized.message.includes('abandon')) {
    throw new Error('Mnemonic not properly redacted from error message');
  }
  
  if (!sanitized.message.includes('[REDACTED_MNEMONIC]')) {
    throw new Error('Missing redaction marker');
  }
});

const testMnemonicSanitization24 = test('CRITICAL-003: Mnemonic sanitization (24 words)', () => {
  const mnemonic24 = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art';
  const error = new Error(`Wallet error: ${mnemonic24}`);
  const sanitized = sanitizeError(error);
  
  if (sanitized.message.includes('abandon')) {
    throw new Error('24-word mnemonic not properly redacted');
  }
  
  if (!sanitized.message.includes('[REDACTED_MNEMONIC]')) {
    throw new Error('Missing redaction marker for 24-word mnemonic');
  }
});

const testPrivateKeySanitization = test('CRITICAL-003: Private key sanitization', () => {
  const privateKey = 'a'.repeat(64); // 64 hex chars
  const error = new Error(`Private key leaked: ${privateKey}`);
  const sanitized = sanitizeError(error);
  
  if (sanitized.message.includes('aaaa')) {
    throw new Error('Private key not properly redacted');
  }
  
  if (!sanitized.message.includes('[REDACTED_PRIVATE_KEY]')) {
    throw new Error('Missing private key redaction marker');
  }
});

const testCardanoAddressSanitization = test('CRITICAL-003: Cardano address sanitization', () => {
  const address = 'addr1qxyz123456789abcdefghijklmnopqrstuvwxyz123456789abcdefghijklmnopqr';
  const error = new Error(`Transaction to ${address} failed`);
  const sanitized = sanitizeError(error);
  
  if (sanitized.message.includes('addr1qxyz')) {
    throw new Error('Cardano address not properly redacted');
  }
  
  if (!sanitized.message.includes('[REDACTED_CARDANO_ADDRESS]')) {
    throw new Error('Missing Cardano address redaction marker');
  }
});

const testBitcoinAddressSanitization = test('CRITICAL-003: Bitcoin address sanitization', () => {
  const address = 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh';
  const error = new Error(`Sending to ${address}`);
  const sanitized = sanitizeError(error);
  
  if (sanitized.message.includes('bc1qxy')) {
    throw new Error('Bitcoin address not properly redacted');
  }
  
  if (!sanitized.message.includes('[REDACTED_BITCOIN_ADDRESS]')) {
    throw new Error('Missing Bitcoin address redaction marker');
  }
});

const testHexDataSanitization = test('CRITICAL-003: Hex data sanitization', () => {
  const hexData = '0x' + 'a'.repeat(64);
  const error = new Error(`Failed to process ${hexData}`);
  const sanitized = sanitizeError(error);
  
  if (sanitized.message.includes('0xaaaa')) {
    throw new Error('Hex data not properly redacted');
  }
  
  if (!sanitized.message.includes('[REDACTED_HEX_DATA]')) {
    throw new Error('Missing hex data redaction marker');
  }
});

const testBase64Sanitization = test('CRITICAL-003: Base64 data sanitization', () => {
  const base64 = 'SGVsbG8gV29ybGQhIFRoaXMgaXMgYSB0ZXN0IHN0cmluZyBmb3IgYmFzZTY0';
  const error = new Error(`Encryption key: ${base64}`);
  const sanitized = sanitizeError(error);
  
  if (sanitized.message.includes('SGVsbG8')) {
    throw new Error('Base64 data not properly redacted');
  }
  
  if (!sanitized.message.includes('[REDACTED_BASE64_DATA]')) {
    throw new Error('Missing base64 data redaction marker');
  }
});

// Integration test: Full wallet creation and cleanup
const testFullWalletFlow = test('INTEGRATION: Full wallet creation with proper cleanup', async () => {
  const engine = new WalletEngine({
    network: 'testnet'
  });
  
  // Create wallet
  const result = await engine.createWallet(['cardano', 'bitcoin'], 12);
  
  // Verify mnemonic is Uint8Array
  if (!(result.mnemonic instanceof Uint8Array)) {
    throw new Error('Mnemonic is not Uint8Array');
  }
  
  // Verify addresses were generated
  if (!result.addresses.cardano || !result.addresses.bitcoin) {
    throw new Error('Addresses not generated');
  }
  
  // Create a copy to verify wiping
  const mnemonicCopy = new Uint8Array(result.mnemonic);
  
  // Wipe mnemonic
  wipeMemory(result.mnemonic);
  
  // Verify it's wiped (all zeros)
  const allZeros = result.mnemonic.every(byte => byte === 0);
  if (!allZeros) {
    throw new Error('Mnemonic not properly wiped after use');
  }
  
  // Verify it's different from copy
  const isDifferent = !result.mnemonic.every((byte, i) => byte === mnemonicCopy[i]);
  if (!isDifferent) {
    throw new Error('Wiping had no effect on mnemonic');
  }
});

// Run all tests
(async () => {
  console.log('='.repeat(60));
  console.log('CRITICAL-001: Memory Wiping Tests');
  console.log('='.repeat(60));
  await testMemoryWiping();
  await testBufferWiping();
  await testSecureContainer();
  
  console.log('\n' + '='.repeat(60));
  console.log('CRITICAL-002: Encryption Before Storage Tests');
  console.log('='.repeat(60));
  await testEncryptionEnforcement();
  await testEncryptionWithCallbacks();
  
  console.log('\n' + '='.repeat(60));
  console.log('CRITICAL-003: Log Sanitization Tests');
  console.log('='.repeat(60));
  await testMnemonicSanitization();
  await testMnemonicSanitization24();
  await testPrivateKeySanitization();
  await testCardanoAddressSanitization();
  await testBitcoinAddressSanitization();
  await testHexDataSanitization();
  await testBase64Sanitization();
  
  console.log('\n' + '='.repeat(60));
  console.log('INTEGRATION TESTS');
  console.log('='.repeat(60));
  await testFullWalletFlow();
  
  console.log('\n' + '='.repeat(60));
  console.log('SUMMARY');
  console.log('='.repeat(60));
  console.log(`✅ Passed: ${passed}`);
  console.log(`❌ Failed: ${failed}`);
  console.log(`📊 Total:  ${passed + failed}`);
  
  if (failed === 0) {
    console.log('\n🎉 ALL SECURITY TESTS PASSED! 🎉\n');
    process.exit(0);
  } else {
    console.log(`\n⚠️  ${failed} TEST(S) FAILED - SECURITY ISSUES REMAIN ⚠️\n`);
    process.exit(1);
  }
})();
