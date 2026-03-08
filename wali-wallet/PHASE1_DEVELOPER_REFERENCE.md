# Phase 1 Developer Reference - Quick Integration Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser Extension                        │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  popup.tsx  │→ │ WalletStore  │→ │  WalletBridge    │   │
│  │   (UI)      │  │  (Zustand)   │  │  (Integration)   │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└──────────────────────────────────────────┬──────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    │                                             │
         ┌──────────▼──────────┐                    ┌────────────▼─────────┐
         │   WalletEngine      │                    │  NightChainIntegration│
         │  (Multi-chain Core) │                    │  (Encrypted Backup)   │
         └──────────┬──────────┘                    └───────────────────────┘
                    │
      ┌─────────────┼─────────────┐
      │             │             │
┌─────▼──────┐ ┌───▼────┐ ┌─────▼──────┐
│ Cardano    │ │Bitcoin │ │   Night    │
│  Wallet    │ │ Wallet │ │   Wallet   │
└─────┬──────┘ └───┬────┘ └─────┬──────┘
      │            │            │
┌─────▼──────┐ ┌───▼────┐ ┌─────▼──────┐
│Blockfrost  │ │Blockstr│ │   Night    │
│    API     │ │eam API │ │ Blockchain │
└────────────┘ └────────┘ └────────────┘
```

---

## Key Files

### Extension Entry Points
- **UI:** `wallet-ui-interface/web-extension/src/popup/index.tsx`
- **Background:** `wallet-ui-interface/web-extension/src/background.ts`
- **Store:** `wallet-ui-interface/web-extension/src/store/wallet.ts`

### Integration Layer
- **Bridge:** `wallet-ui-interface/web-extension/src/wallet-bridge.ts`
- **Config:** `wallet-ui-interface/web-extension/src/config.ts`

### Core Engine
- **Main:** `src/wallet-engine.ts`
- **Cardano:** `src/cardano/wallet.ts`, `src/cardano/blockfrost-api.ts`
- **Bitcoin:** `src/bitcoin/wallet.ts`, `src/bitcoin/api.ts`
- **Night:** `src/night-chain/simple-adapter.ts`

### Security
- **Utils:** `src/utils/security.ts`
- **Encryption:** `src/night-chain/encryption.ts`

---

## API Reference

### WalletBridge

```typescript
import { getWalletBridge } from './wallet-bridge';

const bridge = await getWalletBridge();

// Create wallet with all chains
const result = await bridge.createWallet({
  wordCount: 24,  // 12, 15, 18, 21, or 24
  chains: ['cardano', 'bitcoin', 'night']
});
// Returns: { addresses, mnemonic, requiresBackup }

// Backup to Night Chain
const backup = await bridge.backupToNightChain({
  mnemonic: result.mnemonic,
  accessKey: 'user-key-4-12-chars'
});
// Returns: { success, transactionId, error? }

// Get balances
const balances = await bridge.getBalances(addresses);
// Returns: Array of balance objects

// Get transaction history
const history = await bridge.getTransactionHistory(addresses, 20);
// Returns: Array of transaction objects

// Resolve ADA handle
const address = await bridge.resolveADAHandle('$alice');
// Returns: 'addr1...' or null

// Build transaction
const unsignedTx = await bridge.buildTransaction(
  {
    chain: 'cardano',
    from: 'addr1...',
    to: 'addr1...',
    amount: '10000000' // lovelace
  },
  nightTxId,
  accessKey
);

// Sign and broadcast
const txHash = await bridge.signAndBroadcastTransaction(
  unsignedTx,
  nightTxId,
  accessKey
);
```

---

### WalletStore (Zustand)

```typescript
import { useWalletStore } from './store/wallet';

// In React component
const { 
  createWallet, 
  backupToNightChain,
  getBalance,
  getTransactionHistory,
  processCommand,
  addresses,
  loading,
  error
} = useWalletStore();

// Create wallet
await createWallet(24); // word count

// Backup
await backupToNightChain('user-access-key');

// Get balance
await getBalance(false); // true to show addresses

// Get history
await getTransactionHistory();

// Process natural language command
const response = await processCommand(parsedCommand);
```

---

### WalletEngine

```typescript
import { WalletEngine } from '@wallet-engine/wallet-engine';
import { BlockfrostAPI } from '@wallet-engine/cardano/blockfrost-api';

const engine = new WalletEngine({
  network: 'mainnet',
  blockfrost: {
    projectId: 'mainnet...',
    network: 'mainnet'
  }
});

// Create wallet
const { mnemonic, addresses } = await engine.createWallet(
  ['cardano', 'bitcoin'],
  24
);

// Import wallet
const addresses = await engine.importWallet({
  mnemonic: mnemonicBytes,
  chains: ['cardano', 'bitcoin']
});

// Build transaction
const unsignedTx = await engine.buildTransaction(request, mnemonic);

// Sign transaction
const signedTx = await engine.signTransaction(unsignedTx, mnemonic);

// Broadcast transaction
const txHash = await engine.broadcastTransaction(signedTx);
```

---

## Data Structures

### WalletAddresses
```typescript
interface WalletAddresses {
  cardano?: string;          // addr1...
  bitcoin?: {
    legacy: string;          // 1...
    segwit: string;          // bc1q...
    taproot: string;         // bc1p...
  };
  night?: string;            // night1...
}
```

### Balance
```typescript
interface Balance {
  chain: 'cardano' | 'bitcoin' | 'night';
  balance: string;           // Main balance
  asset: string;             // ADA, BTC, etc.
  tokens?: Array<{
    symbol: string;
    balance: string;
    policyId?: string;
  }>;
}
```

### Transaction
```typescript
interface Transaction {
  hash: string;
  type: 'sent' | 'received';
  amount: string;
  asset: string;
  timestamp: number;
  confirmations?: number;
}
```

---

## Security Guidelines

### ✅ DO
- Always use `Uint8Array` for mnemonics
- Call `wipeMemory()` after using sensitive data
- Encrypt before any storage
- Verify decryption before wiping plaintext
- Use `SecureContainer` for temporary sensitive data

### ❌ DON'T
- Store mnemonics as strings
- Log sensitive data
- Keep mnemonics in memory longer than needed
- Store unencrypted data in chrome.storage
- Use `localStorage` for sensitive data

### Example: Secure Mnemonic Handling
```typescript
// ✅ CORRECT
const mnemonic = generateMnemonic(); // Uint8Array
const container = new SecureContainer(mnemonic);
try {
  // Use mnemonic
  const addr = await generateAddress(container.data);
} finally {
  container.wipe(); // Always wipe
}

// ❌ WRONG
const mnemonic = generateMnemonic().toString(); // String!
localStorage.setItem('mnemonic', mnemonic); // Unencrypted!
```

---

## Configuration

### Blockfrost API Key
**Location:** `wallet-ui-interface/web-extension/src/config.ts`

```typescript
export const BLOCKFROST_MAINNET_KEY = 'mainnetehvvvJVoJUAz5DFJJz2L9fHZmkXlXTMP';
```

### Network Selection
```typescript
const network: 'mainnet' | 'testnet' = 'mainnet';
```

### Night Chain Endpoints
**Location:** `src/night-chain/simple-adapter.ts`

```typescript
const config = {
  network: 'production',
  rpcEndpoint: 'https://night-mainnet.example.com'
};
```

---

## Build & Deploy

### Development Build
```bash
cd wallet-ui-interface/web-extension
npm install
npm run dev  # Watch mode
```

### Production Build
```bash
npm run build  # Minified, optimized
```

### Load Extension
1. Build first
2. `chrome://extensions/`
3. Enable "Developer mode"
4. "Load unpacked" → select `dist/` folder

---

## Debugging

### Enable Console Logs
```typescript
// In wallet-bridge.ts or wallet-engine.ts
console.log('[DEBUG] Wallet created:', addresses);
```

### Chrome DevTools
- **Console:** Check for errors
- **Network:** Inspect Blockfrost/Blockstream calls
- **Application → Storage:** Check chrome.storage.local
- **Application → Service Workers:** Background script logs

### Common Debug Points
```typescript
// WalletBridge
console.log('[WalletBridge] Creating wallet...');

// WalletStore
console.log('[WalletStore] Processing command:', command);

// WalletEngine
console.log('[WalletEngine] Building transaction:', request);
```

---

## Extension Permissions

### Required (manifest.json)
```json
{
  "permissions": [
    "storage",      // For wallet metadata
    "activeTab",    // For dApp integration
    "tabs"          // For dApp connection
  ],
  "host_permissions": [
    "https://cardano-mainnet.blockfrost.io/*",
    "https://blockstream.info/*"
  ]
}
```

---

## Adding New Features

### 1. Add Command Type
**Location:** `wallet-ui-interface/shared/src/types.ts`

```typescript
export interface TransactionIntent {
  type: 'send' | 'delegate' | 'vote' | 'YOUR_NEW_TYPE';
  // ...
}
```

### 2. Add Parser Pattern
**Location:** `wallet-ui-interface/shared/src/parser.ts`

```typescript
if (/your-pattern/i.test(trimmed)) {
  return {
    intent: { type: 'YOUR_NEW_TYPE', chain: 'cardano' },
    confidence: 1.0,
    ambiguities: [],
    rawInput: input,
  };
}
```

### 3. Add Store Handler
**Location:** `wallet-ui-interface/web-extension/src/store/wallet.ts`

```typescript
processCommand: async (command) => {
  if (command.intent.type === 'YOUR_NEW_TYPE') {
    return await yourNewHandler();
  }
}
```

### 4. Add Bridge Method (if needed)
**Location:** `wallet-ui-interface/web-extension/src/wallet-bridge.ts`

```typescript
async yourNewMethod(params: any): Promise<any> {
  // Implementation
}
```

---

## Testing Hooks

### Manual Test Commands
```
create a new wallet
show my balance
show my address
show history
send 10 ADA to addr1...
```

### Automated Testing
```bash
npm test  # Run Jest tests
npm run test:integration  # Integration tests
```

---

## Error Handling

### Error Response Format
```typescript
return {
  success: false,
  message: '❌ User-friendly error message',
  error: error.message  // Technical details
};
```

### Common Errors
- **"Wallet engine not initialized"** → Bridge not ready
- **"Blockfrost API error"** → API key or network issue
- **"Night Chain error"** → Encryption/storage issue
- **"Failed to fetch balance"** → Network or address issue

---

## Performance Tips

### Lazy Loading
```typescript
// Don't import wallet engine until needed
const { WalletEngine } = await import('@wallet-engine/wallet-engine');
```

### Caching
```typescript
// Cache balances for 30 seconds
const CACHE_TTL = 30000;
const cachedBalance = {
  value: null,
  timestamp: 0
};
```

### Background Processing
```typescript
// Use background.ts for heavy operations
chrome.runtime.sendMessage({
  type: 'BUILD_TRANSACTION',
  payload: request
});
```

---

## Resources

### Documentation
- **Blockfrost:** https://docs.blockfrost.io/
- **Cardano Serialization:** https://github.com/Emurgo/cardano-serialization-lib
- **Bitcoin.js:** https://github.com/bitcoinjs/bitcoinjs-lib
- **Zustand:** https://github.com/pmndrs/zustand

### Tools
- **Cardano Explorer:** https://cardanoscan.io/
- **Bitcoin Explorer:** https://blockstream.info/
- **ADA Handle:** https://adahandle.com/

---

## Quick Commands Cheat Sheet

```bash
# Build extension
npm run build

# Watch mode (dev)
npm run dev

# Test
npm test

# Lint
npm run lint

# Generate icons
npm run generate-icons

# Clean build
rm -rf dist && npm run build
```

---

## 🦭 wAli Developer Checklist

Before committing:
- [ ] Code builds without errors
- [ ] No console errors in extension
- [ ] Security review (no plaintext seeds)
- [ ] Tests pass
- [ ] User-facing errors are friendly
- [ ] Documentation updated

---

**Make it WORK. Make it SECURE. Make it wAli!** 🦭
