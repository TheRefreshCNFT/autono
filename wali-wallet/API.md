# Wallet Engine API Documentation

## Overview

The Wallet Engine provides a unified interface for managing Cardano and Bitcoin wallets, including:
- Wallet creation and import
- Address generation
- Balance checking
- Transaction building and signing
- Fee estimation
- Token/asset detection

## Installation

```bash
npm install
npm run build
```

## Quick Start

```typescript
import { WalletEngine } from './wallet-engine';

// Initialize the engine
const engine = new WalletEngine({
  network: 'mainnet',
  cardanoAPI: {
    provider: 'blockfrost',
    apiKey: 'your-blockfrost-api-key',
    network: 'mainnet'
  },
  bitcoinAPI: {
    provider: 'blockstream',
    network: 'mainnet'
  }
});

// Create a new wallet
const wallet = await engine.createWallet(['cardano', 'bitcoin'], 24);
console.log('Mnemonic:', wallet.mnemonic); // STORE SECURELY AND WIPE
console.log('Cardano Address:', wallet.addresses.cardano);
console.log('Bitcoin Address:', wallet.addresses.bitcoin);
```

## Core API

### WalletEngine

The main class for wallet operations.

#### Constructor

```typescript
new WalletEngine(config?: WalletEngineConfig)
```

**Parameters:**
- `config.network`: `'mainnet' | 'testnet'` - Default: `'mainnet'`
- `config.cardanoAPI`: Cardano blockchain API configuration
- `config.bitcoinAPI`: Bitcoin blockchain API configuration

#### Methods

##### createWallet()

Create a new wallet with a generated mnemonic.

```typescript
async createWallet(
  chains?: ('cardano' | 'bitcoin')[],
  wordCount?: 12 | 15 | 18 | 21 | 24
): Promise<WalletCreationResult>
```

**Parameters:**
- `chains`: Array of chains to generate addresses for (default: `['cardano', 'bitcoin']`)
- `wordCount`: Number of words in mnemonic (default: `24`)

**Returns:**
```typescript
{
  mnemonic: string;        // BIP39 mnemonic - MUST BE WIPED AFTER STORING
  addresses: {
    cardano?: string;
    bitcoin?: string;
  };
}
```

**Security Note:** The mnemonic MUST be securely stored (encrypted via Night) and wiped from memory immediately after.

---

##### importWallet()

Import an existing wallet from a mnemonic.

```typescript
async importWallet(options: WalletImportOptions): Promise<{
  cardano?: string;
  bitcoin?: string;
}>
```

**Parameters:**
```typescript
{
  mnemonic: string;                    // BIP39 mnemonic - WILL BE WIPED
  chains: ('cardano' | 'bitcoin')[];
  network?: 'mainnet' | 'testnet';
}
```

**Returns:** Object containing generated addresses for requested chains.

---

##### getBalances()

Get balances for all provided addresses.

```typescript
async getBalances(addresses: {
  cardano?: string;
  bitcoin?: string;
}): Promise<Balance[]>
```

**Returns:**
```typescript
[
  {
    chain: 'cardano',
    address: 'addr1...',
    native: {
      amount: '5000000',    // Lovelace
      symbol: 'ADA',
      decimals: 6
    },
    tokens?: [
      {
        policyId: 'abc123...',
        assetName: '544f4b454e',
        name: 'TOKEN',
        symbol: 'TKN',
        amount: '1000',
        decimals: 0
      }
    ]
  },
  {
    chain: 'bitcoin',
    address: 'bc1...',
    native: {
      amount: '100000',     // Satoshis
      symbol: 'BTC',
      decimals: 8
    }
  }
]
```

---

##### getTransactionHistory()

Get transaction history across all chains.

```typescript
async getTransactionHistory(
  addresses: { cardano?: string; bitcoin?: string },
  limit?: number
): Promise<Transaction[]>
```

**Parameters:**
- `addresses`: Addresses to fetch history for
- `limit`: Maximum number of transactions per chain (default: `50`)

**Returns:** Array of `Transaction` objects sorted by timestamp (most recent first).

---

##### buildTransaction()

Build an unsigned transaction.

```typescript
async buildTransaction(
  request: TransactionBuildRequest,
  mnemonic: string
): Promise<UnsignedTransaction>
```

**Parameters:**
```typescript
{
  chain: 'cardano' | 'bitcoin';
  from: string;                    // Sender address
  to: string;                      // Recipient address (or $handle for Cardano)
  amount: string;                  // In lovelace or satoshis
  tokens?: Array<{                 // Cardano only
    policyId?: string;
    assetName?: string;
    amount: string;
  }>;
  metadata?: any;                  // Optional metadata
}
```

**Returns:**
```typescript
{
  chain: 'cardano' | 'bitcoin';
  raw: string;                     // Unsigned transaction hex
  fee: string;
  preview: {
    from: string;
    to: string;
    amount: string;
    fee: string;
    total: string;
    tokens?: TokenBalance[];
  };
}
```

**Security Note:** Mnemonic is wiped from memory after use.

---

##### signTransaction()

Sign an unsigned transaction.

```typescript
async signTransaction(
  unsignedTx: UnsignedTransaction,
  mnemonic: string
): Promise<SignedTransaction>
```

**Returns:**
```typescript
{
  chain: 'cardano' | 'bitcoin';
  txHash: string;                  // Empty until broadcasted
  raw: string;                     // Signed transaction hex
}
```

**Security Note:** Mnemonic is wiped from memory after use.

---

##### broadcastTransaction()

Broadcast a signed transaction to the network.

```typescript
async broadcastTransaction(signedTx: SignedTransaction): Promise<string>
```

**Returns:** Transaction hash (txid).

---

##### getFeeEstimates()

Get current fee estimates for all configured chains.

```typescript
async getFeeEstimates(): Promise<FeeEstimate[]>
```

**Returns:**
```typescript
[
  {
    chain: 'cardano',
    slow: '170000',
    medium: '200000',
    fast: '250000',
    unit: 'lovelace'
  },
  {
    chain: 'bitcoin',
    slow: '1',
    medium: '5',
    fast: '10',
    unit: 'sat/vB'
  }
]
```

---

##### resolveADAHandle()

Resolve an ADA handle to an address.

```typescript
async resolveADAHandle(handle: string): Promise<ADAHandle | null>
```

**Parameters:**
- `handle`: ADA handle (with or without `$` prefix)

**Returns:**
```typescript
{
  handle: '$alice',
  address: 'addr1...',
  metadata?: any
} | null
```

---

##### validateAddress()

Validate an address for a specific chain.

```typescript
validateAddress(address: string, chain: 'cardano' | 'bitcoin'): boolean
```

**Returns:** `true` if valid, `false` otherwise.

---

## Security Utilities

### SecureContainer

A container that auto-wipes sensitive data.

```typescript
import { SecureContainer } from './utils/security';

const container = new SecureContainer('sensitive-mnemonic');

// Use the data
const mnemonic = container.data;

// Wipe when done
container.wipe();

// Further access throws error
container.data; // Throws: "Attempted to access wiped secure data"
```

### sanitizeError()

Sanitize error messages to prevent sensitive data leakage.

```typescript
import { sanitizeError } from './utils/security';

try {
  // Some operation
} catch (error) {
  const safe = sanitizeError(error);
  console.log(safe.message); // Sensitive data redacted
}
```

Automatically redacts:
- Private keys (64 hex chars)
- Cardano addresses
- Bitcoin addresses
- Mnemonics (12-24 words)

---

## Chain-Specific APIs

### CardanoWallet

Low-level Cardano wallet operations.

```typescript
import { CardanoWallet } from './cardano/wallet';

const wallet = new CardanoWallet('mainnet');

// Generate address
const addr = await wallet.generateAddress(mnemonic, accountIndex, addressIndex);

// Build transaction
const tx = await wallet.buildTransaction(
  fromAddress,
  toAddress,
  amountLovelace,
  utxos,
  changeAddress,
  ttl
);

// Sign transaction
const signed = await wallet.signTransaction(txBodyHex, mnemonic, accountIndex, addressIndex);
```

### BitcoinWallet

Low-level Bitcoin wallet operations.

```typescript
import { BitcoinWallet } from './bitcoin/wallet';

const wallet = new BitcoinWallet('mainnet');

// Generate address
const addr = await wallet.generateAddress(
  mnemonic,
  'native-segwit', // 'legacy' | 'segwit' | 'native-segwit'
  accountIndex,
  addressIndex
);

// Build PSBT
const tx = await wallet.buildTransaction(
  fromAddress,
  toAddress,
  amountSatoshis,
  utxos,
  changeAddress,
  feeRate
);

// Sign PSBT
const signed = await wallet.signTransaction(psbt, mnemonic, addressType, accountIndex, addressIndex);
```

### CardanoAPI

Cardano blockchain API client (Blockfrost/Koios).

```typescript
import { CardanoAPI } from './cardano/api';

const api = new CardanoAPI({
  provider: 'blockfrost',
  apiKey: 'your-api-key',
  network: 'mainnet'
});

// Get balance
const balance = await api.getBalance(address);

// Get UTXOs
const utxos = await api.getUTXOs(address);

// Submit transaction
const txHash = await api.submitTransaction(signedTxHex);

// Resolve ADA handle
const address = await api.resolveADAHandle('$alice');
```

### BitcoinAPI

Bitcoin blockchain API client (Blockstream/Mempool).

```typescript
import { BitcoinAPI } from './bitcoin/api';

const api = new BitcoinAPI({
  provider: 'blockstream',
  network: 'mainnet'
});

// Get balance
const balance = await api.getBalance(address);

// Get UTXOs
const utxos = await api.getUTXOs(address);

// Submit transaction
const txHash = await api.submitTransaction(signedTxHex);

// Estimate fees
const fees = await api.estimateFees();
```

---

## Error Handling

All methods throw sanitized errors that don't leak sensitive data:

```typescript
try {
  await engine.buildTransaction(request, mnemonic);
} catch (error) {
  console.error(error.code);    // Error code
  console.error(error.message); // Safe error message
}
```

Common error codes:
- `CARDANO_ERROR` - Cardano operation failed
- `BITCOIN_ERROR` - Bitcoin operation failed
- `UNKNOWN_ERROR` - Unspecified error

---

## Testing

Run the test suite:

```bash
npm test
```

Run specific tests:

```bash
npm test -- wallet-engine.test.ts
npm test -- security.test.ts
```

---

## Integration with Night

### Storing Mnemonics

```typescript
// 1. Create wallet
const wallet = await engine.createWallet(['cardano', 'bitcoin'], 24);

// 2. Encrypt mnemonic with Night
const encrypted = await nightEngine.encrypt(wallet.mnemonic);

// 3. Store encrypted data
await storage.save('wallet-mnemonic', encrypted);

// 4. WIPE mnemonic from memory immediately
const container = new SecureContainer(wallet.mnemonic);
container.wipe();
```

### Retrieving and Using

```typescript
// 1. Load encrypted mnemonic
const encrypted = await storage.load('wallet-mnemonic');

// 2. Decrypt with Night
const mnemonic = await nightEngine.decrypt(encrypted);

// 3. Use for transaction
const tx = await engine.buildTransaction(request, mnemonic);

// 4. WIPE immediately
const container = new SecureContainer(mnemonic);
container.wipe();
```

---

## Best Practices

### Security

1. **Never log mnemonics or private keys**
2. **Always wipe sensitive data after use**
3. **Validate all addresses before transactions**
4. **Use transaction preview before signing**
5. **Encrypt mnemonics at rest with Night**

### Performance

1. **Cache addresses** - Don't regenerate from mnemonic repeatedly
2. **Batch API calls** - Fetch multiple balances together
3. **Reuse engine instances** - Don't create new engines per operation

### Error Handling

1. **Always catch and handle errors**
2. **Use sanitized errors for logging/display**
3. **Validate inputs before operations**
4. **Check API availability before calls**

---

## Example: Complete Transaction Flow

```typescript
import { WalletEngine, SecureContainer } from './wallet-engine';

async function sendCardano(
  engine: WalletEngine,
  encryptedMnemonic: string,
  fromAddress: string,
  toAddress: string,
  amount: string
) {
  // 1. Decrypt mnemonic
  const mnemonic = await nightEngine.decrypt(encryptedMnemonic);
  const mnemonicContainer = new SecureContainer(mnemonic);

  try {
    // 2. Build transaction
    const unsignedTx = await engine.buildTransaction({
      chain: 'cardano',
      from: fromAddress,
      to: toAddress,
      amount: amount
    }, mnemonicContainer.data);

    // 3. Show preview to user
    console.log('Preview:', unsignedTx.preview);
    const confirmed = await getUserConfirmation();
    
    if (!confirmed) {
      throw new Error('User cancelled transaction');
    }

    // 4. Sign transaction
    const signedTx = await engine.signTransaction(
      unsignedTx,
      mnemonicContainer.data
    );

    // 5. Broadcast
    const txHash = await engine.broadcastTransaction(signedTx);

    console.log('Transaction sent:', txHash);
    return txHash;

  } finally {
    // 6. Always wipe mnemonic
    mnemonicContainer.wipe();
  }
}
```

---

## Support

For issues or questions:
1. Check this documentation
2. Review test files for usage examples
3. Check error messages (they're designed to be helpful)

---

## License

[Your License Here]
