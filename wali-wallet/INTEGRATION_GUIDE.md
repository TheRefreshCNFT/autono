# Integration Guide for UI and Night Agents

This guide explains how to integrate the wallet core engine with the UI and Night encryption layers.

---

## For the UI Agent

### Installation

```typescript
import { WalletEngine } from './wallet-core-engine/src';
```

### Required Configuration

```typescript
const engine = new WalletEngine({
  network: 'mainnet', // or 'testnet'
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
```

### UI Flows

#### 1. Wallet Creation Flow

```typescript
// User clicks "Create New Wallet"
async function handleCreateWallet() {
  try {
    // Step 1: Create wallet
    const wallet = await engine.createWallet(['cardano', 'bitcoin'], 24);
    
    // Step 2: Show mnemonic to user (CRITICAL: one-time display)
    showMnemonicBackupScreen(wallet.mnemonic);
    
    // Step 3: User confirms they've written it down
    await waitForUserConfirmation();
    
    // Step 4: Encrypt with Night
    const encrypted = await nightEngine.encrypt(wallet.mnemonic);
    
    // Step 5: Store encrypted mnemonic
    await storage.saveEncryptedSeed(encrypted);
    
    // Step 6: Wipe plaintext immediately
    new SecureContainer(wallet.mnemonic).wipe();
    
    // Step 7: Store addresses (not sensitive)
    await storage.saveAddresses({
      cardano: wallet.addresses.cardano,
      bitcoin: wallet.addresses.bitcoin
    });
    
    // Step 8: Navigate to wallet home
    navigate('/wallet');
    
  } catch (error) {
    showError(sanitizeError(error).message);
  }
}
```

#### 2. Balance Display Flow

```typescript
async function fetchBalances() {
  try {
    const addresses = await storage.getAddresses();
    
    const balances = await engine.getBalances(addresses);
    
    // Update UI with balances
    updateBalanceDisplay(balances);
    
    // Format for display
    balances.forEach(balance => {
      const amount = formatBalance(
        balance.native.amount,
        balance.native.decimals,
        balance.native.symbol
      );
      
      displayBalance(balance.chain, amount);
      
      // Show tokens if any
      if (balance.tokens) {
        displayTokens(balance.chain, balance.tokens);
      }
    });
    
  } catch (error) {
    showError('Failed to fetch balances');
  }
}

function formatBalance(amount: string, decimals: number, symbol: string): string {
  const value = BigInt(amount);
  const divisor = BigInt(10 ** decimals);
  const whole = value / divisor;
  const fraction = value % divisor;
  
  return `${whole}.${fraction.toString().padStart(decimals, '0')} ${symbol}`;
}
```

#### 3. Send Transaction Flow

```typescript
async function handleSendTransaction(recipient: string, amount: string, chain: 'cardano' | 'bitcoin') {
  try {
    const addresses = await storage.getAddresses();
    const fromAddress = chain === 'cardano' ? addresses.cardano : addresses.bitcoin;
    
    // Step 1: Validate recipient address
    const isValid = engine.validateAddress(recipient, chain);
    if (!isValid) {
      // If Cardano and starts with $, try to resolve handle
      if (chain === 'cardano' && recipient.startsWith('$')) {
        const resolved = await engine.resolveADAHandle(recipient);
        if (!resolved) {
          throw new Error('Invalid ADA handle');
        }
        recipient = resolved.address;
      } else {
        throw new Error('Invalid recipient address');
      }
    }
    
    // Step 2: Decrypt mnemonic (requires user auth)
    await showAuthenticationDialog();
    const encrypted = await storage.getEncryptedSeed();
    const mnemonic = await nightEngine.decrypt(encrypted);
    const mnemonicContainer = new SecureContainer(mnemonic);
    
    try {
      // Step 3: Build transaction
      const unsignedTx = await engine.buildTransaction({
        chain,
        from: fromAddress!,
        to: recipient,
        amount: convertToSmallestUnit(amount, chain) // lovelace or satoshis
      }, mnemonicContainer.data);
      
      // Step 4: Show preview to user
      const confirmed = await showTransactionPreview({
        from: unsignedTx.preview.from,
        to: unsignedTx.preview.to,
        amount: formatAmount(unsignedTx.preview.amount, chain),
        fee: formatAmount(unsignedTx.preview.fee, chain),
        total: formatAmount(unsignedTx.preview.total, chain)
      });
      
      if (!confirmed) {
        throw new Error('Transaction cancelled by user');
      }
      
      // Step 5: Sign transaction
      const signedTx = await engine.signTransaction(unsignedTx, mnemonicContainer.data);
      
      // Step 6: Broadcast
      showLoadingSpinner('Broadcasting transaction...');
      const txHash = await engine.broadcastTransaction(signedTx);
      
      // Step 7: Show success
      showSuccess(`Transaction sent! Hash: ${txHash}`);
      
      // Step 8: Refresh balance
      await fetchBalances();
      
    } finally {
      // CRITICAL: Always wipe mnemonic
      mnemonicContainer.wipe();
    }
    
  } catch (error) {
    showError(sanitizeError(error).message);
  }
}

function convertToSmallestUnit(amount: string, chain: 'cardano' | 'bitcoin'): string {
  const decimals = chain === 'cardano' ? 6 : 8;
  const multiplier = BigInt(10 ** decimals);
  const value = parseFloat(amount);
  const smallest = BigInt(Math.floor(value * Number(multiplier)));
  return smallest.toString();
}
```

#### 4. Transaction History Flow

```typescript
async function fetchTransactionHistory() {
  try {
    const addresses = await storage.getAddresses();
    
    const history = await engine.getTransactionHistory(addresses, 50);
    
    // Sort by timestamp (most recent first) - already done by engine
    displayTransactionHistory(history);
    
  } catch (error) {
    showError('Failed to fetch transaction history');
  }
}

function displayTransactionHistory(transactions: Transaction[]) {
  transactions.forEach(tx => {
    const date = new Date(tx.timestamp);
    const status = tx.status === 'confirmed' 
      ? `✓ ${tx.confirmations} confirmations`
      : 'Pending...';
    
    addTransactionToUI({
      hash: tx.hash,
      date: date.toLocaleString(),
      status,
      chain: tx.chain,
      fee: tx.fee,
      inputs: tx.inputs,
      outputs: tx.outputs
    });
  });
}
```

#### 5. Import Wallet Flow

```typescript
async function handleImportWallet(mnemonic: string) {
  try {
    // Step 1: Validate mnemonic (will throw if invalid)
    const addresses = await engine.importWallet({
      mnemonic,
      chains: ['cardano', 'bitcoin']
    });
    
    // Step 2: Encrypt with Night
    const encrypted = await nightEngine.encrypt(mnemonic);
    
    // Step 3: Store encrypted mnemonic
    await storage.saveEncryptedSeed(encrypted);
    
    // Step 4: Wipe plaintext
    new SecureContainer(mnemonic).wipe();
    
    // Step 5: Store addresses
    await storage.saveAddresses(addresses);
    
    // Step 6: Navigate to wallet
    navigate('/wallet');
    
  } catch (error) {
    showError('Invalid mnemonic phrase');
  }
}
```

### UI Components Needed

1. **Mnemonic Backup Screen**
   - Display 24 words in 3 columns
   - Warning about writing them down
   - Confirmation checkbox
   - "I've written it down" button

2. **Transaction Preview Modal**
   - From/To addresses (truncated with copy button)
   - Amount in large text
   - Fee amount
   - Total (amount + fee)
   - Cancel / Confirm buttons

3. **Balance Display**
   - Native balance (ADA/BTC)
   - Token list (Cardano)
   - Refresh button
   - Loading states

4. **Transaction History**
   - List of transactions
   - Date, status, amount
   - Click to view details
   - Pagination

---

## For the Night Agent

### Integration Points

#### 1. Encrypt Wallet Seed

```typescript
async function encryptWalletSeed(mnemonic: string): Promise<NightAsset> {
  // Create Night asset
  const asset = await nightEngine.createAsset({
    type: 'wallet-seed',
    name: 'Wallet Recovery Phrase',
    data: Buffer.from(mnemonic, 'utf8'),
    metadata: {
      createdAt: Date.now(),
      chains: ['cardano', 'bitcoin']
    }
  });
  
  // Wipe plaintext
  new SecureContainer(mnemonic).wipe();
  
  return asset;
}
```

#### 2. Decrypt for Transaction

```typescript
async function decryptForTransaction(assetId: string): Promise<string> {
  // Require user authentication
  await nightEngine.authenticate();
  
  // Decrypt asset
  const asset = await nightEngine.getAsset(assetId);
  const mnemonic = asset.data.toString('utf8');
  
  // Log access (audit trail)
  await nightEngine.logAccess(assetId, 'transaction-signing');
  
  return mnemonic;
  // CALLER MUST WIPE after use!
}
```

#### 3. Recovery Flow

```typescript
async function recoverWallet(recoveryKit: RecoveryKit): Promise<void> {
  // Use Night's recovery mechanism
  const mnemonic = await nightEngine.recover(recoveryKit);
  
  // Re-import wallet
  const addresses = await walletEngine.importWallet({
    mnemonic,
    chains: ['cardano', 'bitcoin']
  });
  
  // Re-encrypt with new Night key
  const newAsset = await encryptWalletSeed(mnemonic);
  
  // Wipe plaintext
  new SecureContainer(mnemonic).wipe();
  
  // Save addresses
  await storage.saveAddresses(addresses);
}
```

#### 4. Access Control

```typescript
// Night should enforce access control for wallet operations
const accessPolicy: AccessPolicy = {
  asset: 'wallet-seed',
  operations: {
    'transaction-signing': {
      requireAuth: true,
      maxFrequency: '10/hour', // Rate limiting
      requireConfirmation: true
    },
    'wallet-export': {
      requireAuth: true,
      requireConfirmation: true,
      cooldown: '24h' // Prevent rapid export
    }
  }
};
```

### Security Recommendations for Night

1. **Multi-Factor Authentication**
   - Require biometric/PIN for decryption
   - Time-based restrictions (e.g., no large transactions at 3am)
   - Geolocation checks for suspicious activity

2. **Rate Limiting**
   - Max transactions per hour
   - Max decrypt operations per day
   - Alert on unusual patterns

3. **Audit Trail**
   - Log every decrypt operation
   - Record transaction amounts
   - Track failed authentication attempts

4. **Recovery Mechanisms**
   - Social recovery (trusted contacts)
   - Time-locked recovery
   - Hardware key backup

---

## Storage Schema

### Local Storage (Unencrypted)

```typescript
interface WalletStorage {
  addresses: {
    cardano?: string;
    bitcoin?: string;
  };
  metadata: {
    createdAt: number;
    lastUsed: number;
    chains: string[];
  };
}
```

### Night Storage (Encrypted)

```typescript
interface NightAsset {
  id: string;
  type: 'wallet-seed';
  data: Buffer; // Encrypted mnemonic
  metadata: {
    createdAt: number;
    chains: string[];
    version: number;
  };
}
```

---

## Error Handling

### User-Friendly Error Messages

```typescript
const ERROR_MESSAGES = {
  'CARDANO_ERROR': 'Cardano transaction failed. Please try again.',
  'BITCOIN_ERROR': 'Bitcoin transaction failed. Please try again.',
  'INSUFFICIENT_FUNDS': 'Insufficient balance to complete this transaction.',
  'INVALID_ADDRESS': 'The recipient address is invalid.',
  'NETWORK_ERROR': 'Network connection failed. Please check your internet.',
  'AUTH_FAILED': 'Authentication failed. Please try again.',
  'TRANSACTION_REJECTED': 'Transaction was rejected by the network.',
};

function handleWalletError(error: WalletError): string {
  return ERROR_MESSAGES[error.code] || 'An unexpected error occurred.';
}
```

---

## Testing Integration

### Mock Wallet Engine for UI Tests

```typescript
const mockWalletEngine = {
  createWallet: jest.fn().mockResolvedValue({
    mnemonic: 'test mnemonic...',
    addresses: {
      cardano: 'addr_test1...',
      bitcoin: 'tb1...'
    }
  }),
  
  getBalances: jest.fn().mockResolvedValue([
    {
      chain: 'cardano',
      address: 'addr_test1...',
      native: { amount: '5000000', symbol: 'ADA', decimals: 6 },
      tokens: []
    }
  ]),
  
  buildTransaction: jest.fn().mockResolvedValue({
    chain: 'cardano',
    raw: 'tx_hex',
    fee: '170000',
    preview: {
      from: 'addr1...',
      to: 'addr1...',
      amount: '1000000',
      fee: '170000',
      total: '1170000'
    }
  })
};
```

---

## Configuration Management

### Environment Variables

```bash
# .env file
BLOCKFROST_API_KEY=mainnet_xxxxxxxxxxxx
NETWORK=mainnet
ENABLE_TESTNET=false
MAX_TX_PER_HOUR=10
AUTH_TIMEOUT_MS=300000
```

### Runtime Configuration

```typescript
const config = {
  network: process.env.NETWORK === 'mainnet' ? 'mainnet' : 'testnet',
  cardanoAPI: {
    provider: 'blockfrost',
    apiKey: process.env.BLOCKFROST_API_KEY,
    network: process.env.NETWORK as NetworkType
  },
  bitcoinAPI: {
    provider: 'blockstream',
    network: process.env.NETWORK as NetworkType
  },
  security: {
    maxTransactionsPerHour: 10,
    authTimeoutMs: 300000,
    requireConfirmationAbove: {
      cardano: '100000000', // 100 ADA
      bitcoin: '10000000'   // 0.1 BTC
    }
  }
};
```

---

## Deployment Checklist

- [ ] Install dependencies (`npm install`)
- [ ] Build wallet engine (`npm run build`)
- [ ] Configure API keys (Blockfrost/Koios)
- [ ] Set up Night encryption
- [ ] Test wallet creation flow
- [ ] Test transaction flow
- [ ] Test recovery flow
- [ ] Enable error monitoring
- [ ] Set up rate limiting
- [ ] Configure backup strategy
- [ ] Test on testnet first
- [ ] Security audit

---

## Performance Optimization

### Caching Strategy

```typescript
// Cache addresses to avoid re-derivation
const addressCache = new Map<string, { cardano?: string; bitcoin?: string }>();

// Cache balances with TTL
const balanceCache = new TTLCache<string, Balance>(60000); // 1 minute TTL

// Debounce balance fetches
const debouncedFetchBalances = debounce(fetchBalances, 1000);
```

### Batch Operations

```typescript
// Fetch balances for multiple addresses in parallel
const balances = await Promise.all([
  engine.getBalances({ cardano: addr1 }),
  engine.getBalances({ bitcoin: addr2 })
]);
```

---

## Monitoring & Analytics

### Key Metrics to Track

1. **Wallet Operations**
   - Wallet creations per day
   - Import vs. create ratio
   - Active wallets

2. **Transactions**
   - Transactions per day (per chain)
   - Average transaction value
   - Failed transaction rate
   - Average fee paid

3. **Performance**
   - API response times
   - Transaction build time
   - Signing time

4. **Security**
   - Failed authentication attempts
   - Unusual transaction patterns
   - API errors

---

## Support & Maintenance

### Common Issues

**Q: Transaction fails with "Insufficient funds"**
A: Check that balance > (amount + fee). Fetch latest balance before building transaction.

**Q: Invalid address error**
A: Use `validateAddress()` before building transaction. For Cardano, check if it's an ADA handle.

**Q: Mnemonic won't import**
A: Verify it's a valid BIP39 phrase (12, 15, 18, 21, or 24 words).

---

**Integration complete!** The wallet engine is ready to be consumed by UI and Night agents.
