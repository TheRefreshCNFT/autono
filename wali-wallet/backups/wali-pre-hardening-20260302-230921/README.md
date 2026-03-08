# Wallet Engine - Core Module

A secure, production-ready wallet engine for Cardano and Bitcoin integration. Built with TypeScript and designed for the Night wallet project.

## Features

✅ **Dual Chain Support**
- Cardano (via cardano-serialization-lib)
- Bitcoin (via bitcoinjs-lib)

✅ **Security First**
- Memory-only key operations
- Automatic sensitive data wiping
- Error message sanitization
- No disk writes before encryption

✅ **Complete Wallet Operations**
- Wallet creation & import (BIP39)
- Address generation (BIP44/CIP-1852)
- Balance checking with token support
- Transaction building & signing
- Fee estimation
- Transaction history

✅ **Cardano-Specific**
- Native token (CNT) detection
- ADA handle resolution ($handle → addr1...)
- Proper UTXO management
- Metadata support

✅ **Bitcoin-Specific**
- Multiple address types (Legacy, SegWit, Native SegWit)
- PSBT support
- Dynamic fee estimation
- UTXO selection

## Quick Start

### Installation

```bash
npm install
npm run build
```

### Basic Usage

```typescript
import { WalletEngine } from './src';

// Initialize
const engine = new WalletEngine({
  network: 'mainnet',
  cardanoAPI: {
    provider: 'blockfrost',
    apiKey: process.env.BLOCKFROST_API_KEY,
    network: 'mainnet'
  },
  bitcoinAPI: {
    provider: 'blockstream',
    network: 'mainnet'
  }
});

// Create new wallet
const wallet = await engine.createWallet(['cardano', 'bitcoin'], 24);
console.log('Addresses:', wallet.addresses);

// ⚠️ IMPORTANT: Store mnemonic securely and wipe immediately
// await storeInNight(wallet.mnemonic);
// wipeMnemonic(wallet.mnemonic);
```

## Architecture

```
src/
├── types/              # TypeScript type definitions
├── utils/              # Security utilities
├── cardano/            
│   ├── wallet.ts       # Cardano wallet operations
│   └── api.ts          # Blockchain API client
├── bitcoin/
│   ├── wallet.ts       # Bitcoin wallet operations
│   └── api.ts          # Blockchain API client
├── wallet-engine.ts    # Main unified API
└── index.ts            # Public exports
```

## Security Model

### Sensitive Data Handling

1. **Mnemonics** - Generated in memory, must be encrypted (via Night) before storage
2. **Private Keys** - Derived on-demand, never persisted
3. **Seed Phrases** - Wiped immediately after key derivation
4. **Error Messages** - Automatically sanitized to prevent leakage

### SecureContainer Pattern

```typescript
import { SecureContainer } from './src/utils/security';

const container = new SecureContainer(mnemonic);

try {
  // Use the data
  const result = await wallet.signTransaction(tx, container.data);
} finally {
  // Always wipe
  container.wipe();
}
```

### Transaction Flow Security

```
User Input → Validation → Build Tx → Preview → User Confirm → Sign → Broadcast
                ↓                         ↓           ↓
           Sanitize           Show Details    Wipe Keys
```

## API Overview

### Core Operations

| Method | Purpose | Security |
|--------|---------|----------|
| `createWallet()` | Generate new wallet | Returns mnemonic (MUST WIPE) |
| `importWallet()` | Import from mnemonic | Auto-wipes mnemonic |
| `getBalances()` | Fetch balances + tokens | Safe |
| `buildTransaction()` | Build unsigned tx | Auto-wipes mnemonic |
| `signTransaction()` | Sign transaction | Auto-wipes mnemonic |
| `broadcastTransaction()` | Submit to network | Safe |

### Validation & Utilities

| Method | Purpose |
|--------|---------|
| `validateAddress()` | Check address format |
| `resolveADAHandle()` | Convert $handle → addr1... |
| `getFeeEstimates()` | Get current network fees |

See [API.md](./API.md) for complete documentation.

## Testing

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific test suite
npm test -- wallet-engine.test.ts
```

### Test Coverage

- ✅ Wallet creation (12/15/18/21/24 words)
- ✅ Address generation (Cardano & Bitcoin)
- ✅ Address derivation consistency
- ✅ Transaction building & signing
- ✅ Security utilities (wiping, sanitization)
- ✅ Error handling
- ✅ Multi-chain operations

## Integration with Night

The wallet engine is designed to work seamlessly with the Night encryption layer:

```typescript
// Create wallet
const wallet = await engine.createWallet(['cardano', 'bitcoin'], 24);

// Encrypt with Night
const encryptedMnemonic = await nightEngine.encrypt(wallet.mnemonic);

// Store encrypted asset
await nightStorage.save('wallet-seed', encryptedMnemonic);

// Wipe plaintext immediately
new SecureContainer(wallet.mnemonic).wipe();

// Later: retrieve and use
const mnemonic = await nightEngine.decrypt(encryptedMnemonic);
const tx = await engine.buildTransaction(request, mnemonic);
new SecureContainer(mnemonic).wipe();
```

## Configuration

### Cardano API Providers

**Blockfrost** (Recommended)
```typescript
cardanoAPI: {
  provider: 'blockfrost',
  apiKey: 'your-project-id',
  network: 'mainnet'
}
```

**Koios** (Free, no API key)
```typescript
cardanoAPI: {
  provider: 'koios',
  network: 'mainnet'
}
```

### Bitcoin API Providers

**Blockstream** (Recommended)
```typescript
bitcoinAPI: {
  provider: 'blockstream',
  network: 'mainnet'
}
```

**Mempool.space**
```typescript
bitcoinAPI: {
  provider: 'mempool',
  network: 'mainnet'
}
```

## Error Handling

All errors are sanitized to prevent sensitive data leakage:

```typescript
try {
  await engine.buildTransaction(request, mnemonic);
} catch (error) {
  // Safe to log/display
  console.error(error.message); // No addresses, keys, or mnemonics
  
  // Error codes for programmatic handling
  if (error.code === 'CARDANO_ERROR') {
    // Handle Cardano-specific error
  }
}
```

## Dependencies

### Core
- `@emurgo/cardano-serialization-lib-nodejs` - Cardano operations
- `bitcoinjs-lib` - Bitcoin operations
- `bip39` - Mnemonic generation/validation
- `@scure/bip32` - HD key derivation
- `axios` - API requests

### Development
- `typescript` - Type safety
- `jest` - Testing framework
- `ts-jest` - TypeScript testing

## Roadmap

### Phase 1: Core ✅ (Complete)
- [x] Wallet creation/import
- [x] Address generation
- [x] Transaction building
- [x] Security utilities

### Phase 2: API Integration ✅ (Complete)
- [x] Balance queries
- [x] Transaction history
- [x] Fee estimation
- [x] ADA handle resolution

### Phase 3: Advanced Features (Planned)
- [ ] Hardware wallet support (Ledger/Trezor)
- [ ] Multi-signature wallets
- [ ] Staking operations (Cardano)
- [ ] Lightning Network (Bitcoin)
- [ ] NFT operations
- [ ] DApp connector

## Contributing

This is part of the Night wallet project. Contributions should:
1. Follow the security-first approach
2. Include tests for all critical paths
3. Maintain TypeScript strict mode compliance
4. Document sensitive data handling

## License

[Your License Here]

## Support

For integration help, see:
- [API.md](./API.md) - Complete API reference
- Test files (`__tests__/`) - Usage examples
- Error messages - Designed to be helpful

---

**⚠️ Security Notice:** This wallet engine handles sensitive cryptographic material. Always:
- Encrypt mnemonics before storage (use Night)
- Wipe sensitive data from memory after use
- Validate all addresses before transactions
- Show transaction previews to users
- Never log private keys or mnemonics
