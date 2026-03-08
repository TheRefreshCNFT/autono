# Night Chain Integration - Quick Start

## 🚀 Installation

No additional dependencies needed - uses Node.js built-in `crypto` module.

## ✅ Verify Installation

```bash
# Run tests
npx ts-node src/night-chain/__tests__/run-simple-test.ts

# Run demo
npx ts-node src/night-chain/examples/demo.ts
```

## 📦 Basic Usage

### 1. Store Seed Phrases

```typescript
import { createNightChainStorage } from './src/night-chain';

// Initialize
const storage = await createNightChainStorage('testnet');

// Store
const result = await storage.storeSeedPhrases({
  cardanoMnemonic: 'word1 word2 ... word24',
  bitcoinMnemonic: 'word1 word2 ... word12',
  timestamp: Date.now()
}, 'mykey123'); // 4-12 char access key

console.log('Asset ID:', result.assetId);
// Plaintext is now wiped!
```

### 2. Recover Seed Phrases

```typescript
// Start recovery
const challengeId = await storage.startRecovery(assetId);

// Line 1
let state = storage.submitRecoveryInput(challengeId, 'word1 word2 word3 word4');
console.log('Bot:', state.botLine1);

// Line 2
state = storage.submitRecoveryInput(challengeId, 'word5 word6 word7 word8');
console.log('Bot:', state.botLine2);

// Decrypt
const bundle = await storage.completeRecovery(challengeId, 'mykey123');
console.log('Recovered:', bundle.cardanoMnemonic);
```

## 🔒 Security Features

- **AES-256-GCM** encryption
- **100,000 PBKDF2** iterations
- **3 strikes** rate limiting (15 min lock)
- **Round-trip verification** before wiping
- **Access key never logged**

## 📚 Documentation

- **Full API**: `src/night-chain/README.md`
- **Integration Guide**: `src/night-chain/INTEGRATION_GUIDE.md`
- **Implementation Details**: `NIGHT_CHAIN_IMPLEMENTATION.md`
- **Test Results**: `SUBAGENT_COMPLETION_REPORT.md`

## ⚡ Test Results

```
✓ All tests completed!
  Passed: 43
  Failed: 0
```

## 🎯 Key Files

| File | Purpose |
|------|---------|
| `src/night-chain/integration.ts` | Main API |
| `src/night-chain/encryption.ts` | AES-256-GCM engine |
| `src/night-chain/recovery-dialog.ts` | 4-line dialog |
| `src/night-chain/access-control.ts` | Rate limiting |

## 🔗 Integration

### With Wallet Core Engine

```typescript
const nightStorage = await createNightChainStorage('testnet');
const result = await nightStorage.storeSeedPhrases(bundle, accessKey);
return { assetId: result.assetId };
```

### With UI Agent

```typescript
const challengeId = await nightStorage.startRecovery(assetId);
const line1 = await promptUser('4 words:');
const state = nightStorage.submitRecoveryInput(challengeId, line1);
// ... complete dialog ...
const bundle = await nightStorage.completeRecovery(challengeId, key);
```

## ✨ Status

**✅ COMPLETE** - All deliverables implemented and tested

- ✅ Night wallet creation
- ✅ AES-256-GCM encryption (100k iterations)
- ✅ On-chain asset storage
- ✅ 4-line recovery dialog
- ✅ 3-strike rate limiting
- ✅ 43/43 tests passing
- ✅ Full documentation

## 🎮 Try It Now

```bash
# Quick test
npx ts-node src/night-chain/__tests__/run-simple-test.ts

# Full demo (3 scenarios)
npx ts-node src/night-chain/examples/demo.ts
```

## 📞 Need Help?

See detailed guides:
- `src/night-chain/README.md` - Complete API reference
- `src/night-chain/INTEGRATION_GUIDE.md` - Step-by-step integration
- `src/night-chain/examples/demo.ts` - Working examples

---

**Ready to integrate!** 🚀
