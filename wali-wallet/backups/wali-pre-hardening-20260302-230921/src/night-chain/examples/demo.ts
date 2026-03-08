/**
 * Night Chain Integration Demo
 * 
 * This demonstrates the complete workflow for:
 * 1. Storing seed phrases securely
 * 2. Recovering them using the 4-line dialog
 * 3. Handling access control
 */

import {
  createNightChainStorage,
  NightChainSecureStorage
} from '../index';
import type { SeedPhraseBundle } from '../types';

/**
 * Demo: Complete storage and recovery workflow
 */
async function demoCompleteWorkflow() {
  console.log('\n=== NIGHT CHAIN SECURE STORAGE DEMO ===\n');
  
  // Step 1: Initialize
  console.log('Step 1: Initializing Night chain storage...');
  const storage = await createNightChainStorage('testnet');
  console.log('✓ Initialized');
  console.log('✓ Wallet address:', storage.getWalletAddress());
  console.log('');
  
  // Step 2: Prepare seed phrases (would come from wallet-core-engine)
  console.log('Step 2: Preparing seed phrases...');
  const seedBundle: SeedPhraseBundle = {
    cardanoMnemonic: 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about',
    bitcoinMnemonic: 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon',
    timestamp: Date.now()
  };
  console.log('✓ Seed phrases prepared');
  console.log('');
  
  // Step 3: Define access key
  const accessKey = 'demo1234';
  console.log('Step 3: Access key defined (4-12 chars)');
  console.log('✓ Access key: ********');
  console.log('');
  
  // Step 4: Store on Night chain
  console.log('Step 4: Storing seed phrases on Night chain...');
  console.log('  → Encrypting with AES-256-GCM');
  console.log('  → Deriving key from access key (PBKDF2, 100k iterations)');
  console.log('  → Verifying encryption round-trip');
  console.log('  → Submitting to blockchain');
  console.log('  → Verifying asset accessibility');
  console.log('  → Wiping plaintext from memory');
  
  const txResult = await storage.storeSeedPhrases(seedBundle, accessKey);
  
  console.log('✓ Storage complete!');
  console.log('  Transaction Hash:', txResult.txHash);
  console.log('  Asset ID:', txResult.assetId);
  console.log('  Status:', txResult.status);
  console.log('  Block Height:', txResult.blockHeight);
  console.log('');
  
  // Step 5: Simulate time passing / user losing device
  console.log('--- SIMULATING USER LOSING DEVICE ---');
  console.log('User needs to recover seed phrases from Night chain');
  console.log('');
  
  // Step 6: Start recovery
  console.log('Step 5: Starting recovery process...');
  const challengeId = await storage.startRecovery(txResult.assetId);
  console.log('✓ Recovery challenge created');
  console.log('  Challenge ID:', challengeId);
  console.log('');
  
  // Step 7: Recovery Dialog - Line 1
  console.log('Step 6: Recovery Dialog (4-line challenge/response)');
  console.log('');
  console.log('--- Line 1 ---');
  console.log('USER: Provides 4 words from seed phrase');
  const userLine1 = 'abandon abandon abandon abandon';
  console.log(`[You - Line 1]: ${userLine1}`);
  
  let dialogState = storage.submitRecoveryInput(challengeId, userLine1);
  console.log(`[Bot - Line 1]: ${dialogState.botLine1}`);
  console.log('');
  
  // Step 8: Recovery Dialog - Line 2
  console.log('--- Line 2 ---');
  console.log('USER: Provides 4 DIFFERENT words from seed phrase');
  const userLine2 = 'abandon abandon abandon about';
  console.log(`[You - Line 2]: ${userLine2}`);
  
  dialogState = storage.submitRecoveryInput(challengeId, userLine2);
  console.log(`[Bot - Line 2]: ${dialogState.botLine2}`);
  console.log('');
  
  console.log('✓ Recovery dialog complete');
  console.log('');
  
  // Step 9: Complete recovery with access key
  console.log('Step 7: Completing recovery with access key...');
  console.log('  → Decrypting asset from Night chain');
  console.log('  → Verifying access key');
  console.log('  → Extracting seed phrases');
  
  const recoveredBundle = await storage.completeRecovery(challengeId, accessKey);
  
  console.log('✓ Recovery successful!');
  console.log('');
  console.log('Recovered seed phrases:');
  console.log('  Cardano:', recoveredBundle.cardanoMnemonic?.substring(0, 30) + '...');
  console.log('  Bitcoin:', recoveredBundle.bitcoinMnemonic?.substring(0, 30) + '...');
  console.log('');
  
  // Step 10: Verify integrity
  console.log('Step 8: Verifying integrity...');
  const match = recoveredBundle.cardanoMnemonic === seedBundle.cardanoMnemonic &&
                recoveredBundle.bitcoinMnemonic === seedBundle.bitcoinMnemonic;
  console.log('✓ Integrity check:', match ? 'PASSED' : 'FAILED');
  console.log('');
  
  // Step 11: Show stats
  console.log('Step 9: Access statistics');
  const stats = storage.getAccessStats();
  console.log('  Total assets:', stats.totalAssets);
  console.log('  Locked assets:', stats.lockedAssets);
  console.log('  Assets with failures:', stats.assetsWithFailures);
  console.log('');
  
  // Cleanup
  await storage.disconnect();
  console.log('✓ Disconnected');
  console.log('');
  console.log('=== DEMO COMPLETE ===\n');
}

/**
 * Demo: Access control and rate limiting
 */
async function demoAccessControl() {
  console.log('\n=== ACCESS CONTROL DEMO ===\n');
  
  const storage = await createNightChainStorage('testnet');
  
  // Store asset
  const bundle: SeedPhraseBundle = {
    cardanoMnemonic: 'test test test test test test test test test test test test',
    timestamp: Date.now()
  };
  
  const correctKey = 'correct1';
  const wrongKey = 'wrong999';
  
  console.log('Storing asset with access key...');
  const txResult = await storage.storeSeedPhrases(bundle, correctKey);
  console.log('✓ Asset stored:', txResult.assetId);
  console.log('');
  
  console.log('Attempting recovery with WRONG access key...');
  
  for (let attempt = 1; attempt <= 3; attempt++) {
    console.log(`\n--- Attempt ${attempt} ---`);
    
    try {
      const challengeId = await storage.startRecovery(txResult.assetId);
      storage.submitRecoveryInput(challengeId, 'test test test test');
      storage.submitRecoveryInput(challengeId, 'word word word word');
      
      await storage.completeRecovery(challengeId, wrongKey);
      console.log('✗ Should have failed!');
    } catch (error: any) {
      console.log('✓ Decryption failed (expected)');
      console.log('  Error:', error.message);
      
      const stats = storage.getAccessStats();
      console.log('  Failed attempts:', stats.assetsWithFailures);
    }
  }
  
  console.log('\n--- Attempt 4 (should be locked) ---');
  try {
    await storage.startRecovery(txResult.assetId);
    console.log('✗ Should have been locked!');
  } catch (error: any) {
    console.log('✓ Asset locked (expected)');
    console.log('  Error:', error.message);
  }
  
  console.log('\n✓ Access control working correctly');
  console.log('  Asset is locked for 15 minutes after 3 failed attempts');
  
  await storage.disconnect();
  console.log('\n=== ACCESS CONTROL DEMO COMPLETE ===\n');
}

/**
 * Demo: Multiple assets
 */
async function demoMultipleAssets() {
  console.log('\n=== MULTIPLE ASSETS DEMO ===\n');
  
  const storage = await createNightChainStorage('testnet');
  
  console.log('Storing multiple seed phrase backups...\n');
  
  // Store 3 different backups
  for (let i = 1; i <= 3; i++) {
    const bundle: SeedPhraseBundle = {
      cardanoMnemonic: `backup${i} `.repeat(12).trim(),
      bitcoinMnemonic: `backup${i} `.repeat(12).trim(),
      timestamp: Date.now()
    };
    
    const accessKey = `key${i}000`;
    
    console.log(`Backup ${i}:`);
    const result = await storage.storeSeedPhrases(bundle, accessKey);
    console.log('  Asset ID:', result.assetId);
    console.log('  Tx Hash:', result.txHash);
    console.log('');
    
    // Small delay to ensure different timestamps
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  console.log('Listing all stored assets...\n');
  const assets = storage.listStoredAssets();
  
  console.log(`Total assets: ${assets.length}`);
  assets.forEach((asset, idx) => {
    console.log(`\nAsset ${idx + 1}:`);
    console.log('  ID:', asset.assetId);
    console.log('  Created:', new Date(asset.createdAt).toISOString());
    console.log('  Algorithm:', asset.metadata.algorithm);
    console.log('  Key Derivation:', asset.metadata.keyDerivation);
    console.log('  Iterations:', asset.metadata.iterations);
  });
  
  await storage.disconnect();
  console.log('\n=== MULTIPLE ASSETS DEMO COMPLETE ===\n');
}

/**
 * Run all demos
 */
async function runAllDemos() {
  try {
    await demoCompleteWorkflow();
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    await demoAccessControl();
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    await demoMultipleAssets();
    
    console.log('\n✓ All demos completed successfully!\n');
  } catch (error) {
    console.error('\n✗ Demo failed:', error);
    process.exit(1);
  }
}

// Run demos if executed directly
if (require.main === module) {
  runAllDemos();
}

export {
  demoCompleteWorkflow,
  demoAccessControl,
  demoMultipleAssets,
  runAllDemos
};
