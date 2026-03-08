# Night Chain Secure Storage Integration

Secure on-chain storage for seed phrases using the Midnight/Night blockchain with AES-256-GCM encryption.

## Overview

This module provides a complete solution for storing seed phrases (Cardano and Bitcoin) securely on the Night blockchain with the following features:

- **End-to-end encryption**: AES-256-GCM with PBKDF2 key derivation
- **Access control**: User-defined access key (4-12 characters)
- **Recovery mechanism**: 4-line challenge/response dialog
- **Rate limiting**: 3 failed attempts lock asset for 15 minutes
- **Verification**: Round-trip encryption test before wiping plaintext

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Application                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           NightChainSecureStorage (Main API)                 │
├─────────────────────────────────────────────────────────────┤
│  • storeSeedPhrases()      • startRecovery()                │
│  • completeRecovery()      • getAccessStats()               │
└───┬─────────┬────────┬─────────┬──────────┬────────────────┘
    │         │        │         │          │
    ▼         ▼        ▼         ▼          ▼
┌────────┐ ┌──────┐ ┌─────┐ ┌────────┐ ┌──────────┐
│ Wallet │ │Crypto│ │Asset│ │Recovery│ │  Access  │
│ Client │ │Engine│ │Store│ │ Dialog │ │ Control  │
└────────┘ └──────┘ └─────┘ └────────┘ └──────────┘
    │         │        │         │          │
    └─────────┴────────┴─────────┴──────────┘
                      │
                      ▼
            ┌──────────────────┐
            │ Night Blockchain │
            │  (Midnight Net)  │
            └──────────────────┘
```

## Security Model

### Encryption

- **Algorithm**: AES-256-GCM (authenticated encryption)
- **Key Derivation**: PBKDF2-SHA256 with 100,000 iterations
- **Key Source**: User access key (4-12 characters)
- **Nonce**: 96-bit random IV per encryption
- **Salt**: 256-bit random salt per encryption
- **Auth Tag**: 128-bit GCM authentication tag

### Access Control

- **Max Attempts**: 3 failed decryption attempts
- **Lock Duration**: 15 minutes after 3 failures
- **Auto-Reset**: Attempts reset on successful access
- **No Logging**: Access keys never logged or stored

### Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Seed Phrases │────▶│  Encrypt +   │────▶│   Store on   │
│  (Plaintext) │     │   Verify     │     │ Night Chain  │
└──────────────┘     └──────────────┘     └──────────────┘
                             │
                             ▼
                     ┌──────────────┐
                     │ Wipe Original│
                     │  (CRITICAL)  │
                     └──────────────┘
```

## Usage

### 1. Initialize Storage

```typescript
import { createNightChainStorage } from './night-chain';

const storage = await createNightChainStorage('testnet');
```

### 2. Store Seed Phrases

```typescript
const bundle = {
  cardanoMnemonic: 'word1 word2 word3 ... word24',
  bitcoinMnemonic: 'word1 word2 word3 ... word12',
  timestamp: Date.now()
};

const accessKey = 'mykey123'; // 4-12 characters

const result = await storage.storeSeedPhrases(bundle, accessKey);
console.log('Asset ID:', result.assetId);
console.log('Tx Hash:', result.txHash);
```

**CRITICAL**: After this call completes, plaintext seed phrases are wiped from memory.

### 3. Recovery Process

#### Step 1: Start Recovery

```typescript
const assetId = 'asset_xxx...';
const challengeId = await storage.startRecovery(assetId);
```

#### Step 2: 4-Line Dialog

```typescript
// User Line 1: User provides 4 words
let state = storage.submitRecoveryInput(challengeId, 'word1 word2 word3 word4');
console.log('Bot Line 1:', state.botLine1);

// User Line 2: User provides 4 different words
state = storage.submitRecoveryInput(challengeId, 'word5 word6 word7 word8');
console.log('Bot Line 2:', state.botLine2);
```

#### Step 3: Complete Recovery

```typescript
const recoveredBundle = await storage.completeRecovery(challengeId, accessKey);
console.log('Cardano:', recoveredBundle.cardanoMnemonic);
console.log('Bitcoin:', recoveredBundle.bitcoinMnemonic);
```

### 4. Access Control

```typescript
// Check remaining attempts
const stats = storage.getAccessStats();
console.log('Locked assets:', stats.lockedAssets);

// Note: Access is automatically locked after 3 failed attempts
// Lock expires after 15 minutes
```

## API Reference

### NightChainSecureStorage

#### `initialize(): Promise<void>`
Initialize the Night chain client and create/load wallet.

#### `storeSeedPhrases(bundle: SeedPhraseBundle, accessKey: string): Promise<NightTransactionResult>`
Encrypt and store seed phrases on Night chain.

**Parameters:**
- `bundle`: Seed phrase bundle (Cardano/Bitcoin mnemonics)
- `accessKey`: User's access key (4-12 chars, never stored)

**Returns:** Transaction result with asset ID

**Security:**
1. Validates access key length
2. Encrypts with AES-256-GCM
3. Verifies round-trip encryption
4. Stores on blockchain
5. Verifies asset accessibility
6. Wipes plaintext from memory

#### `startRecovery(assetId: string): Promise<string>`
Start recovery process for an asset.

**Returns:** Challenge ID for recovery dialog

**Checks:**
- Asset exists
- Not locked due to failed attempts

#### `submitRecoveryInput(challengeId: string, input: string): RecoveryDialogState`
Submit user input to recovery dialog.

**Parameters:**
- `challengeId`: Challenge ID from `startRecovery()`
- `input`: 4 space-separated words

**Returns:** Updated dialog state

#### `completeRecovery(challengeId: string, accessKey: string): Promise<SeedPhraseBundle>`
Complete recovery and decrypt seed phrases.

**Parameters:**
- `challengeId`: Challenge ID
- `accessKey`: User's access key

**Returns:** Decrypted seed phrase bundle

**Throws:**
- `DECRYPTION_FAILED`: Wrong access key
- Locks asset after 3 failed attempts

#### `getWalletAddress(): string | null`
Get Night wallet address.

#### `listStoredAssets(): EncryptedAsset[]`
List all stored assets for current wallet.

#### `getAccessStats(): AccessStats`
Get access control statistics.

#### `disconnect(): Promise<void>`
Disconnect and cleanup.

## Types

### SeedPhraseBundle

```typescript
interface SeedPhraseBundle {
  cardanoMnemonic?: string;
  bitcoinMnemonic?: string;
  timestamp: number;
  checksum?: string;
}
```

### NightTransactionResult

```typescript
interface NightTransactionResult {
  txHash: string;
  assetId: string;
  status: 'pending' | 'confirmed' | 'failed';
  blockHeight?: number;
  timestamp: number;
}
```

### RecoveryDialogState

```typescript
interface RecoveryDialogState {
  step: 'user-line-1' | 'bot-line-1' | 'user-line-2' | 'bot-line-2' | 'complete';
  userLine1?: string;
  botLine1?: string;
  userLine2?: string;
  botLine2?: string;
  challengeId: string;
  assetId: string;
}
```

## Testing

Run the integration test suite:

```bash
npm test -- src/night-chain/__tests__/integration.test.ts
```

Tests cover:
- ✓ Encryption/decryption round-trip
- ✓ Invalid access key rejection
- ✓ Wallet creation
- ✓ Asset storage and retrieval
- ✓ Recovery dialog flow
- ✓ Access control and rate limiting
- ✓ End-to-end storage and recovery
- ✓ Security requirements (PBKDF2 iterations, wiping)

## Integration with Wallet Core

### Receiving Seed Phrases from Wallet Core

```typescript
// In wallet-core-engine agent
const { cardanoMnemonic, bitcoinMnemonic } = await generateWallets();

// Pass to Night chain integration
const nightStorage = await createNightChainStorage('testnet');
const result = await nightStorage.storeSeedPhrases({
  cardanoMnemonic,
  bitcoinMnemonic,
  timestamp: Date.now()
}, userAccessKey);

// At this point, plaintext is wiped
console.log('Seed phrases secured on Night chain');
console.log('Asset ID:', result.assetId);
```

### Coordinating with UI Agent

```typescript
// In UI agent - recovery dialog
async function handleRecovery(assetId: string) {
  const challengeId = await nightStorage.startRecovery(assetId);
  
  // Prompt user for line 1
  const line1 = await promptUser('Enter 4 words from your seed phrase:');
  let state = nightStorage.submitRecoveryInput(challengeId, line1);
  
  // Show bot response
  displayMessage(`Bot: ${state.botLine1}`);
  
  // Prompt user for line 2
  const line2 = await promptUser('Enter 4 different words:');
  state = nightStorage.submitRecoveryInput(challengeId, line2);
  
  // Show bot response
  displayMessage(`Bot: ${state.botLine2}`);
  
  // Get access key
  const accessKey = await promptSecure('Enter access key:');
  
  // Complete recovery
  try {
    const bundle = await nightStorage.completeRecovery(challengeId, accessKey);
    displayMessage('Recovery successful!');
    return bundle;
  } catch (error) {
    displayError('Recovery failed. Check your access key.');
  }
}
```

## Production Considerations

### Current Implementation

This is a **proof-of-concept** implementation. The following components are **simulated**:

- ❌ Night blockchain transactions (simulated with random hashes)
- ❌ On-chain storage (cached locally)
- ❌ Wallet key management (simplified Ed25519)

### Production Requirements

For production deployment, you need:

1. **Midnight SDK Integration**
   - Install official Midnight SDK: `npm install @midnight-network/sdk`
   - Use real wallet creation, signing, and transaction submission
   - Connect to actual Midnight network nodes

2. **Secure Key Storage**
   - Store Night wallet private keys in hardware security module (HSM)
   - Use platform keychain/keystore for access key derivation
   - Implement secure enclave integration on mobile

3. **Network Configuration**
   - Configure proper RPC endpoints for mainnet/testnet
   - Implement retry logic and connection pooling
   - Handle network failures gracefully

4. **Monitoring & Logging**
   - Log all recovery attempts (without exposing keys)
   - Monitor failed access patterns
   - Alert on suspicious activity

5. **Backup & Recovery**
   - Implement multi-device recovery sync
   - Support social recovery (trusted contacts)
   - Emergency recovery procedures

## License

This module is part of the wallet-core-engine project.

## Support

For issues or questions:
- Check test suite for usage examples
- Review inline code documentation
- Contact wallet-core-engine team
