# Night Chain Integration Guide

This guide explains how to integrate the Night chain secure storage module with the wallet-core-engine and UI agents.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Agent                      │
│  • Collects user access key (4-12 chars)                   │
│  • Displays recovery dialog (4-line challenge/response)     │
│  • Shows confirmation messages                              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              Wallet Core Engine Agent                        │
│  • Generates Cardano/Bitcoin seed phrases                   │
│  • Passes phrases to Night chain module                     │
│  • Coordinates storage workflow                             │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│           Night Chain Secure Storage Module                  │
│  • Encrypts seed phrases (AES-256-GCM)                      │
│  • Stores encrypted assets on Night blockchain             │
│  • Manages recovery dialog                                  │
│  • Enforces access control (3 strikes)                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              Night/Midnight Blockchain                       │
│  • Stores encrypted assets with ZK proofs                   │
│  • Provides private data storage                            │
│  • Returns asset IDs for retrieval                          │
└─────────────────────────────────────────────────────────────┘
```

## Integration Steps

### 1. Wallet Core Engine → Night Chain

The wallet-core-engine agent should pass seed phrases to Night chain immediately after generation.

#### Example Implementation

```typescript
// In wallet-core-engine agent

import { createNightChainStorage } from './night-chain';
import type { SeedPhraseBundle } from './night-chain/types';

export class WalletCoreEngine {
  private nightStorage: NightChainSecureStorage | null = null;
  
  async initialize() {
    // Initialize Night chain storage
    this.nightStorage = await createNightChainStorage('testnet');
    console.log('[Wallet Core] Night chain storage initialized');
  }
  
  async createNewWallet(userAccessKey: string) {
    // Step 1: Generate seed phrases
    console.log('[Wallet Core] Generating seed phrases...');
    const cardanoMnemonic = generateCardanoMnemonic(); // BIP39 24 words
    const bitcoinMnemonic = generateBitcoinMnemonic(); // BIP39 12 words
    
    // Step 2: Derive addresses
    const cardanoAddress = deriveCardanoAddress(cardanoMnemonic);
    const bitcoinAddress = deriveBitcoinAddress(bitcoinMnemonic);
    
    // Step 3: Prepare bundle for Night chain
    const bundle: SeedPhraseBundle = {
      cardanoMnemonic,
      bitcoinMnemonic,
      timestamp: Date.now()
    };
    
    // Step 4: Store securely on Night chain
    if (!this.nightStorage) {
      throw new Error('Night storage not initialized');
    }
    
    console.log('[Wallet Core] Storing seed phrases on Night chain...');
    const txResult = await this.nightStorage.storeSeedPhrases(
      bundle,
      userAccessKey
    );
    
    console.log('[Wallet Core] ✓ Seed phrases secured');
    console.log('[Wallet Core] Asset ID:', txResult.assetId);
    console.log('[Wallet Core] CRITICAL: Plaintext seed phrases wiped');
    
    // Step 5: Return wallet info (WITHOUT seed phrases)
    return {
      cardanoAddress,
      bitcoinAddress,
      nightAssetId: txResult.assetId,
      nightTxHash: txResult.txHash,
      createdAt: Date.now()
    };
  }
  
  async recoverWallet(assetId: string, userAccessKey: string) {
    if (!this.nightStorage) {
      throw new Error('Night storage not initialized');
    }
    
    // Recovery happens via UI agent's dialog
    // This is just the final decryption step
    console.log('[Wallet Core] Starting wallet recovery...');
    
    // Note: Recovery dialog should be handled by UI agent
    // This method assumes dialog is complete
    
    return {
      message: 'Use UI agent to complete recovery dialog',
      assetId
    };
  }
}
```

### 2. UI Agent → Recovery Dialog Flow

The UI agent orchestrates the 4-line recovery dialog with the user.

#### Example Implementation

```typescript
// In UI agent

import { NightChainSecureStorage } from './night-chain';

export class UIAgent {
  private nightStorage: NightChainSecureStorage;
  
  async handleWalletRecovery(assetId: string) {
    console.log('[UI] Starting wallet recovery flow');
    
    // Step 1: Start recovery
    const challengeId = await this.nightStorage.startRecovery(assetId);
    
    // Step 2: Display instructions
    this.displayMessage(`
      === WALLET RECOVERY ===
      
      To recover your wallet, you'll need:
      1. 8 words from your seed phrase (in two sets of 4)
      2. Your access key
      
      This is a secure 4-line challenge/response dialog.
    `);
    
    // Step 3: Line 1 - User input
    const userLine1 = await this.promptUser(
      'Enter the FIRST 4 words from your seed phrase (space-separated):'
    );
    
    let dialogState = this.nightStorage.submitRecoveryInput(
      challengeId,
      userLine1
    );
    
    // Show bot response
    this.displayMessage(`[System]: ${dialogState.botLine1}`);
    
    // Step 4: Line 2 - User input
    const userLine2 = await this.promptUser(
      'Enter 4 DIFFERENT words from your seed phrase:'
    );
    
    dialogState = this.nightStorage.submitRecoveryInput(
      challengeId,
      userLine2
    );
    
    // Show bot response
    this.displayMessage(`[System]: ${dialogState.botLine2}`);
    
    // Step 5: Get access key
    const accessKey = await this.promptSecure(
      'Enter your access key (4-12 characters):',
      { hideInput: true }
    );
    
    // Step 6: Complete recovery
    try {
      this.displayMessage('Decrypting wallet...');
      
      const recoveredBundle = await this.nightStorage.completeRecovery(
        challengeId,
        accessKey
      );
      
      this.displaySuccess(`
        ✓ Wallet recovered successfully!
        
        Your seed phrases have been decrypted.
        Please store them securely.
      `);
      
      // Return to wallet core for restoration
      return {
        success: true,
        bundle: recoveredBundle
      };
      
    } catch (error: any) {
      if (error.message.includes('DECRYPTION_FAILED')) {
        const remainingAttempts = this.extractRemainingAttempts(error.message);
        
        this.displayError(`
          ✗ Incorrect access key
          
          Remaining attempts: ${remainingAttempts}
          ${remainingAttempts === 0 ? 'Asset locked for 15 minutes' : ''}
        `);
      } else if (error.message.includes('Too many failed attempts')) {
        this.displayError(`
          ✗ Asset locked
          
          Too many failed recovery attempts.
          Please try again in 15 minutes.
        `);
      } else {
        this.displayError(`Recovery failed: ${error.message}`);
      }
      
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  private extractRemainingAttempts(errorMsg: string): number {
    const match = errorMsg.match(/(\d+) attempts remaining/);
    return match ? parseInt(match[1]) : 0;
  }
}
```

### 3. Coordinated Workflow

Here's how the three components work together:

#### Wallet Creation Flow

```
┌──────────┐     ┌──────────────┐     ┌─────────────┐
│    UI    │────▶│ Wallet Core  │────▶│Night Chain  │
└──────────┘     └──────────────┘     └─────────────┘
     │                  │                      │
     │ 1. User enters   │                      │
     │    access key    │                      │
     ├─────────────────▶│                      │
     │                  │                      │
     │                  │ 2. Generate mnemonics│
     │                  │                      │
     │                  │ 3. Encrypt & store   │
     │                  ├─────────────────────▶│
     │                  │                      │
     │                  │                  4. Store on
     │                  │                     chain
     │                  │                      │
     │                  │ 5. Asset ID + TxHash │
     │                  │◀─────────────────────┤
     │                  │                      │
     │ 6. Wallet info   │                      │
     │    (no mnemonics)│                      │
     │◀─────────────────┤                      │
     │                  │                      │
     │ 7. Display success                     │
     │                                         │
```

#### Wallet Recovery Flow

```
┌──────────┐     ┌──────────────┐     ┌─────────────┐
│    UI    │────▶│ Wallet Core  │────▶│Night Chain  │
└──────────┘     └──────────────┘     └─────────────┘
     │                  │                      │
     │ 1. User wants to │                      │
     │    recover       │                      │
     │                  │                      │
     │ 2. Start recovery│                      │
     ├──────────────────┼─────────────────────▶│
     │                  │                      │
     │                  │              3. Create
     │                  │                 challenge
     │                  │                      │
     │ 4. Challenge ID  │                      │
     │◀─────────────────┼──────────────────────┤
     │                  │                      │
     │ 5. 4-line dialog │                      │
     │    (2 user, 2 bot)                      │
     │◀────────────────▶│                      │
     │                  │                      │
     │ 6. Enter access  │                      │
     │    key           │                      │
     │                  │                      │
     │ 7. Complete      │                      │
     │    recovery      │                      │
     ├──────────────────┼─────────────────────▶│
     │                  │                      │
     │                  │              8. Decrypt
     │                  │                 with key
     │                  │                      │
     │ 9. Seed phrases  │                      │
     │◀─────────────────┼──────────────────────┤
     │                  │                      │
     │10. Restore wallet│                      │
     ├─────────────────▶│                      │
     │                  │                      │
```

## Configuration

### Network Selection

```typescript
// Development
const storage = await createNightChainStorage('devnet');

// Testing
const storage = await createNightChainStorage('testnet');

// Production
const storage = await createNightChainStorage('mainnet');
```

### Custom Configuration

```typescript
import { NightChainSecureStorage } from './night-chain';
import type { NightWalletConfig } from './night-chain/types';

const config: NightWalletConfig = {
  network: 'testnet',
  rpcEndpoint: 'https://custom-rpc.midnight.network'
};

const storage = new NightChainSecureStorage(config);
await storage.initialize();
```

## Error Handling

### Common Errors

| Error | Meaning | Action |
|-------|---------|--------|
| `Access key must be 4-12 characters` | Invalid access key length | Validate input before submission |
| `INVALID_ACCESS_KEY` | Wrong access key during decryption | Show error, track attempts |
| `DECRYPTION_FAILED` | Wrong access key (with attempt count) | Display remaining attempts |
| `Too many failed attempts` | Asset locked after 3 failures | Show lock duration (15 min) |
| `Asset not found` | Invalid asset ID | Verify asset ID is correct |
| `Recovery dialog not complete` | Tried to decrypt before dialog done | Complete all 4 lines first |

### Error Handling Example

```typescript
try {
  const result = await storage.storeSeedPhrases(bundle, accessKey);
  console.log('Success:', result.assetId);
} catch (error: any) {
  if (error.message.includes('Access key must be')) {
    // Invalid access key format
    showError('Access key must be 4-12 characters');
  } else if (error.message.includes('ENCRYPTION_VERIFICATION_FAILED')) {
    // Encryption round-trip failed (critical)
    showCriticalError('Encryption verification failed. Please try again.');
  } else {
    // Unknown error
    showError('Storage failed: ' + error.message);
  }
}
```

## Security Best Practices

### 1. Access Key Handling

```typescript
// ✓ GOOD: Never log access key
const accessKey = getUserInput();
await storage.storeSeedPhrases(bundle, accessKey);
// Access key never appears in logs

// ✗ BAD: Don't log access key
console.log('Access key:', accessKey); // NEVER DO THIS
```

### 2. Seed Phrase Handling

```typescript
// ✓ GOOD: Pass directly to Night chain, let it wipe
const bundle = { cardanoMnemonic, bitcoinMnemonic, timestamp: Date.now() };
await storage.storeSeedPhrases(bundle, accessKey);
// Phrases are automatically wiped after verification

// ✗ BAD: Don't store in variables after Night chain storage
const backup = cardanoMnemonic; // NEVER DO THIS
await storage.storeSeedPhrases(bundle, accessKey);
console.log(backup); // Phrase still in memory!
```

### 3. Recovery Dialog

```typescript
// ✓ GOOD: Validate input before submission
const input = getUserInput();
if (input.split(' ').length !== 4) {
  showError('Please enter exactly 4 words');
  return;
}
dialogState = storage.submitRecoveryInput(challengeId, input);

// ✗ BAD: Don't skip validation
dialogState = storage.submitRecoveryInput(challengeId, input); // May throw
```

## Testing

### Unit Tests

```bash
npm test -- src/night-chain/__tests__/integration.test.ts
```

### Integration Test with Wallet Core

```typescript
// test/integration.test.ts

import { WalletCoreEngine } from './wallet-core';
import { createNightChainStorage } from './night-chain';

test('should integrate with wallet core', async () => {
  const walletCore = new WalletCoreEngine();
  await walletCore.initialize();
  
  const walletInfo = await walletCore.createNewWallet('test1234');
  
  expect(walletInfo.nightAssetId).toBeDefined();
  expect(walletInfo.cardanoAddress).toBeDefined();
  expect(walletInfo.bitcoinAddress).toBeDefined();
});
```

## Monitoring

### Access Statistics

```typescript
const stats = storage.getAccessStats();
console.log('Total assets:', stats.totalAssets);
console.log('Locked assets:', stats.lockedAssets);
console.log('Assets with failures:', stats.assetsWithFailures);

// Alert if too many locked assets
if (stats.lockedAssets > 10) {
  sendAlert('High number of locked assets detected');
}
```

### Asset Listing

```typescript
const assets = storage.listStoredAssets();

assets.forEach(asset => {
  console.log('Asset ID:', asset.assetId);
  console.log('Created:', new Date(asset.createdAt).toISOString());
  console.log('Algorithm:', asset.metadata.algorithm);
  console.log('Iterations:', asset.metadata.iterations);
});
```

## Production Deployment

### Checklist

- [ ] Replace simulated Night blockchain with actual Midnight SDK
- [ ] Configure production RPC endpoints
- [ ] Implement secure key storage (HSM, keychain)
- [ ] Set up monitoring and alerting
- [ ] Test network failure scenarios
- [ ] Implement backup recovery procedures
- [ ] Review access control logs
- [ ] Conduct security audit
- [ ] Test disaster recovery
- [ ] Document operational procedures

### Migration Path

1. **Phase 1**: Use simulated Night chain for development
2. **Phase 2**: Integrate Midnight SDK testnet
3. **Phase 3**: Security audit and penetration testing
4. **Phase 4**: Deploy to Midnight mainnet
5. **Phase 5**: Monitor and iterate

## Support

For questions or issues:
- Review examples in `src/night-chain/examples/demo.ts`
- Check test cases in `src/night-chain/__tests__/`
- Read inline documentation in source files
- Contact the development team

## Next Steps

1. ✓ Review this integration guide
2. ✓ Run demo: `npx ts-node src/night-chain/examples/demo.ts`
3. ✓ Run tests: `npm test`
4. ✓ Integrate with wallet-core-engine agent
5. ✓ Integrate with UI agent
6. ✓ Test end-to-end workflow
7. ✓ Plan production deployment
