/**
 * Simple test runner (without Jest framework)
 * Run with: npx ts-node src/night-chain/__tests__/run-simple-test.ts
 */

import {
  encryptSeedPhrases,
  decryptSeedPhrases,
  verifyEncryptionRoundTrip,
  createNightChainStorage,
  RecoveryDialogManager,
  AccessKeyControl
} from '../index';
import type { SeedPhraseBundle } from '../types';

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string) {
  if (!condition) {
    console.error(`  ✗ FAILED: ${message}`);
    failed++;
    return false;
  }
  passed++;
  return true;
}

function assertEqual(actual: any, expected: any, message: string) {
  if (actual !== expected) {
    console.error(`  ✗ FAILED: ${message}`);
    console.error(`    Expected: ${expected}`);
    console.error(`    Actual: ${actual}`);
    failed++;
    return false;
  }
  passed++;
  return true;
}

async function testEncryption() {
  console.log('\n=== Testing Encryption Module ===');
  
  const testBundle: SeedPhraseBundle = {
    cardanoMnemonic: 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about',
    bitcoinMnemonic: 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon',
    timestamp: Date.now()
  };
  
  const accessKey = 'test1234';
  
  // Test encryption
  console.log('Test: Encrypt seed phrases');
  const encrypted = encryptSeedPhrases(testBundle, accessKey);
  assert(!!encrypted.encryptedData, 'Encrypted data should exist');
  assert(!!encrypted.nonce, 'Nonce should exist');
  assert(!!encrypted.salt, 'Salt should exist');
  assert(!!encrypted.authTag, 'Auth tag should exist');
  
  // Test decryption
  console.log('Test: Decrypt seed phrases');
  const decrypted = decryptSeedPhrases(encrypted, accessKey);
  assert(decrypted.verified, 'Decryption should be verified');
  
  const recoveredBundle: SeedPhraseBundle = JSON.parse(decrypted.decryptedData);
  assertEqual(recoveredBundle.cardanoMnemonic, testBundle.cardanoMnemonic, 'Cardano mnemonic should match');
  assertEqual(recoveredBundle.bitcoinMnemonic, testBundle.bitcoinMnemonic, 'Bitcoin mnemonic should match');
  
  // Test wrong key
  console.log('Test: Fail decryption with wrong key');
  try {
    decryptSeedPhrases(encrypted, 'wrongkey');
    assert(false, 'Should have thrown error for wrong key');
  } catch (error: any) {
    assert(error.message.includes('INVALID_ACCESS_KEY'), 'Should throw INVALID_ACCESS_KEY error');
  }
  
  // Test round-trip
  console.log('Test: Verify encryption round-trip');
  const verified = verifyEncryptionRoundTrip(testBundle, accessKey);
  assert(verified, 'Round-trip verification should pass');
  
  // Test key length validation
  console.log('Test: Reject short access key');
  try {
    encryptSeedPhrases(testBundle, 'abc');
    assert(false, 'Should reject key shorter than 4 characters');
  } catch (error: any) {
    assert(error.message.includes('4-12 characters'), 'Should mention character requirement');
  }
  
  console.log('✓ Encryption tests complete');
}

async function testWalletCreation() {
  console.log('\n=== Testing Wallet Creation ===');
  
  console.log('Test: Create Night wallet');
  const storage = await createNightChainStorage('testnet');
  
  const address = storage.getWalletAddress();
  assert(!!address, 'Wallet address should exist');
  assert(!!address && address.startsWith('nighttest1'), 'Testnet address should start with nighttest1');
  
  await storage.disconnect();
  console.log('✓ Wallet creation tests complete');
}

async function testAssetStorage() {
  console.log('\n=== Testing Asset Storage ===');
  
  const storage = await createNightChainStorage('testnet');
  
  const testBundle: SeedPhraseBundle = {
    cardanoMnemonic: 'test test test test test test test test test test test test',
    bitcoinMnemonic: 'test test test test test test test test test test test test',
    timestamp: Date.now()
  };
  
  const accessKey = 'secure123';
  
  console.log('Test: Store encrypted asset');
  const txResult = await storage.storeSeedPhrases(testBundle, accessKey);
  assert(!!txResult.txHash, 'Transaction hash should exist');
  assert(!!txResult.assetId, 'Asset ID should exist');
  assertEqual(txResult.status, 'confirmed', 'Status should be confirmed');
  
  console.log('Test: Verify asset is accessible');
  const assets = storage.listStoredAssets();
  assert(assets.length > 0, 'Should have stored assets');
  
  const storedAsset = assets.find(a => a.assetId === txResult.assetId);
  assert(!!storedAsset, 'Should find stored asset');
  
  await storage.disconnect();
  console.log('✓ Asset storage tests complete');
}

async function testRecoveryDialog() {
  console.log('\n=== Testing Recovery Dialog ===');
  
  const manager = new RecoveryDialogManager();
  const assetId = 'asset_test123';
  
  console.log('Test: Start recovery dialog');
  const challengeId = manager.startDialog(assetId);
  assert(!!challengeId, 'Challenge ID should exist');
  
  console.log('Test: Submit user line 1');
  let state = manager.submitUserInput(challengeId, 'abandon ability able about');
  assertEqual(state.step, 'user-line-2', 'Should advance to user-line-2');
  assertEqual(state.userLine1, 'abandon ability able about', 'Should store user line 1');
  assert(!!state.botLine1, 'Bot line 1 should exist');
  
  console.log('Test: Submit user line 2');
  state = manager.submitUserInput(challengeId, 'above absent absorb abstract');
  assertEqual(state.step, 'complete', 'Should complete dialog');
  assertEqual(state.userLine2, 'above absent absorb abstract', 'Should store user line 2');
  assert(!!state.botLine2, 'Bot line 2 should exist');
  
  console.log('Test: Extract recovery phrase');
  const phrase = manager.completeDialog(challengeId);
  assert(phrase.includes('abandon ability able about'), 'Should include line 1 words');
  assert(phrase.includes('above absent absorb abstract'), 'Should include line 2 words');
  
  console.log('Test: Reject non-4-word input');
  const challengeId2 = manager.startDialog('asset_test456');
  try {
    manager.submitUserInput(challengeId2, 'abandon ability able');
    assert(false, 'Should reject non-4-word input');
  } catch (error: any) {
    assert(error.message.includes('exactly 4 words'), 'Should mention 4 words');
  }
  
  console.log('✓ Recovery dialog tests complete');
}

async function testAccessControl() {
  console.log('\n=== Testing Access Control ===');
  
  const control = new AccessKeyControl();
  const assetId = 'asset_access1';
  
  console.log('Test: Allow initial access');
  let result = control.canAttemptAccess(assetId);
  assert(result.allowed, 'Should allow initial access');
  
  console.log('Test: Track failed attempts');
  control.recordFailedAttempt(assetId);
  assertEqual(control.getRemainingAttempts(assetId), 2, 'Should have 2 remaining after 1 failure');
  
  control.recordFailedAttempt(assetId);
  assertEqual(control.getRemainingAttempts(assetId), 1, 'Should have 1 remaining after 2 failures');
  
  control.recordFailedAttempt(assetId);
  assertEqual(control.getRemainingAttempts(assetId), 0, 'Should have 0 remaining after 3 failures');
  
  console.log('Test: Lock after 3 failed attempts');
  assert(control.isLocked(assetId), 'Should be locked after 3 failures');
  
  result = control.canAttemptAccess(assetId);
  assert(!result.allowed, 'Should deny access when locked');
  assert(!!result.reason && result.reason.includes('Too many failed attempts'), 'Should mention too many attempts');
  
  console.log('Test: Reset attempts after success');
  const assetId2 = 'asset_access2';
  control.recordFailedAttempt(assetId2);
  control.recordFailedAttempt(assetId2);
  assertEqual(control.getRemainingAttempts(assetId2), 1, 'Should have 1 remaining');
  
  control.recordSuccessfulAccess(assetId2);
  assertEqual(control.getRemainingAttempts(assetId2), 3, 'Should reset to 3 after success');
  assert(!control.isLocked(assetId2), 'Should not be locked after reset');
  
  console.log('✓ Access control tests complete');
}

async function testEndToEnd() {
  console.log('\n=== Testing End-to-End Recovery ===');
  
  const storage = await createNightChainStorage('testnet');
  
  const originalBundle: SeedPhraseBundle = {
    cardanoMnemonic: 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about',
    bitcoinMnemonic: 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon',
    timestamp: Date.now()
  };
  
  const accessKey = 'recovery1';
  
  console.log('Test: Store seed phrases');
  const txResult = await storage.storeSeedPhrases(originalBundle, accessKey);
  assert(!!txResult.assetId, 'Asset ID should exist');
  
  console.log('Test: Start recovery');
  const challengeId = await storage.startRecovery(txResult.assetId);
  assert(!!challengeId, 'Challenge ID should exist');
  
  console.log('Test: Complete recovery dialog');
  let dialogState = storage.submitRecoveryInput(challengeId, 'abandon ability able about');
  assertEqual(dialogState.step, 'user-line-2', 'Should advance to line 2');
  
  dialogState = storage.submitRecoveryInput(challengeId, 'above absent absorb abstract');
  assertEqual(dialogState.step, 'complete', 'Should complete dialog');
  
  console.log('Test: Decrypt with access key');
  const recoveredBundle = await storage.completeRecovery(challengeId, accessKey);
  assertEqual(recoveredBundle.cardanoMnemonic, originalBundle.cardanoMnemonic, 'Should recover Cardano mnemonic');
  assertEqual(recoveredBundle.bitcoinMnemonic, originalBundle.bitcoinMnemonic, 'Should recover Bitcoin mnemonic');
  
  await storage.disconnect();
  console.log('✓ End-to-end tests complete');
}

async function runAllTests() {
  console.log('\n╔════════════════════════════════════════════════════════╗');
  console.log('║   Night Chain Integration - Test Suite                ║');
  console.log('╚════════════════════════════════════════════════════════╝');
  
  try {
    await testEncryption();
    await testWalletCreation();
    await testAssetStorage();
    await testRecoveryDialog();
    await testAccessControl();
    await testEndToEnd();
    
    console.log('\n' + '='.repeat(60));
    console.log(`\n✓ All tests completed!`);
    console.log(`  Passed: ${passed}`);
    console.log(`  Failed: ${failed}`);
    
    if (failed === 0) {
      console.log('\n🎉 SUCCESS: All tests passed!\n');
      process.exit(0);
    } else {
      console.log(`\n⚠️  FAILURE: ${failed} test(s) failed\n`);
      process.exit(1);
    }
  } catch (error) {
    console.error('\n✗ Test suite crashed:', error);
    process.exit(1);
  }
}

runAllTests();
