# Integration Guide

This document explains how to integrate the conversational wallet UI with the core blockchain components.

## Overview

The wallet UI interfaces with two main backend systems:
1. **wallet-core-engine**: Blockchain operations, transaction building, balance queries
2. **night-chain-security**: Key management, signing, recovery

## Architecture

```
┌─────────────────────────────────────────────────────┐
│          Conversational Wallet UI                   │
│  (Web Extension / Mobile App / Discord Bot)         │
└────────────┬────────────────────────────────────────┘
             │
             ├─────────────────┬──────────────────────┐
             │                 │                      │
             ▼                 ▼                      ▼
    ┌────────────────┐  ┌──────────────┐   ┌─────────────────┐
    │ Command Parser │  │ Transaction  │   │  UI Components  │
    │   (@shared)    │  │   Builder    │   │    (React)      │
    └────────┬───────┘  └──────┬───────┘   └─────────────────┘
             │                 │
             └────────┬────────┘
                      │
          ┌───────────┴────────────┐
          │                        │
          ▼                        ▼
┌──────────────────┐    ┌────────────────────────┐
│ wallet-core-     │    │ night-chain-security   │
│   engine         │    │                        │
│                  │    │                        │
│ • Tx building    │    │ • Key generation       │
│ • Fee estimation │    │ • Transaction signing  │
│ • Submission     │    │ • Recovery management  │
│ • Balance query  │    │ • Secure storage       │
└──────────────────┘    └────────────────────────┘
```

## wallet-core-engine Integration

### Interface Definition

```typescript
// shared/src/wallet-core-engine.interface.ts

export interface WalletCoreEngine {
  // Transaction operations
  buildTransaction(intent: TransactionIntent): Promise<UnsignedTransaction>;
  estimateFee(intent: TransactionIntent): Promise<{ fee: string; feeAsset: Asset }>;
  validateTransaction(intent: TransactionIntent): Promise<{ valid: boolean; warnings: string[] }>;
  submitTransaction(signedTx: SignedTransaction): Promise<string>; // Returns tx hash
  
  // Balance and asset queries
  getBalance(address: string, chain: Chain): Promise<string>;
  getAssets(address: string, chain: Chain): Promise<Asset[]>;
  getTransactionHistory(address: string, chain: Chain, limit?: number): Promise<Transaction[]>;
  
  // Address operations
  resolveHandle(handle: string, chain: Chain): Promise<string | null>;
  validateAddress(address: string, chain: Chain): Promise<boolean>;
  
  // Network operations
  getNetworkStatus(chain: Chain): Promise<NetworkStatus>;
}

export interface UnsignedTransaction {
  chain: Chain;
  txBody: string; // Serialized transaction body
  inputs: TransactionInput[];
  outputs: TransactionOutput[];
  fee: string;
  metadata?: Record<string, any>;
}

export interface SignedTransaction {
  chain: Chain;
  txBody: string;
  witnesses: string[];
  txHash: string;
}
```

### Implementation Example

```typescript
// web-extension/src/services/wallet-engine.ts

import { WalletCoreEngine } from '@wallet-ui/shared';

export class WalletEngineService implements WalletCoreEngine {
  private apiUrl: string;

  constructor(apiUrl: string = 'http://localhost:8080') {
    this.apiUrl = apiUrl;
  }

  async buildTransaction(intent: TransactionIntent): Promise<UnsignedTransaction> {
    const response = await fetch(`${this.apiUrl}/transaction/build`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(intent),
    });

    if (!response.ok) {
      throw new Error('Failed to build transaction');
    }

    return response.json();
  }

  async estimateFee(intent: TransactionIntent): Promise<{ fee: string; feeAsset: Asset }> {
    const response = await fetch(`${this.apiUrl}/transaction/estimate-fee`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(intent),
    });

    return response.json();
  }

  // ... implement other methods
}
```

### Usage in UI

```typescript
// web-extension/src/store/wallet.ts

import { WalletEngineService } from '../services/wallet-engine';

const engine = new WalletEngineService();

export const useWalletStore = create<WalletStore>((set, get) => ({
  processCommand: async (command: ParsedCommand) => {
    // Build transaction
    const unsignedTx = await engine.buildTransaction(command.intent);
    
    // Estimate fee
    const { fee, feeAsset } = await engine.estimateFee(command.intent);
    
    // Create preview
    const preview = {
      intent: command.intent,
      fee,
      feeAsset,
      // ... other fields
    };
    
    return {
      success: true,
      requiresConfirmation: true,
      preview,
    };
  },
}));
```

## night-chain-security Integration

### Interface Definition

```typescript
// shared/src/night-chain-security.interface.ts

export interface SecurityModule {
  // Wallet management
  createWallet(chain: Chain): Promise<WalletInfo>;
  restoreWallet(recoveryPhrase: string, chain: Chain): Promise<WalletInfo>;
  exportRecoveryPhrase(walletId: string): Promise<string>;
  
  // Authentication
  unlock(walletId: string, credentials: Credentials): Promise<boolean>;
  lock(walletId: string): Promise<void>;
  isLocked(walletId: string): Promise<boolean>;
  
  // Signing operations
  signTransaction(walletId: string, unsignedTx: UnsignedTransaction): Promise<SignedTransaction>;
  signData(walletId: string, address: string, payload: string): Promise<Signature>;
  
  // Key operations
  getPublicKey(walletId: string): Promise<string>;
  getAddresses(walletId: string): Promise<string[]>;
  deriveAddress(walletId: string, index: number): Promise<string>;
  
  // Security features
  enableBiometrics(walletId: string): Promise<boolean>;
  verifyBiometrics(walletId: string): Promise<boolean>;
}

export interface WalletInfo {
  id: string;
  chain: Chain;
  addresses: {
    receiving: string;
    change?: string;
  };
  publicKey: string;
}

export interface Credentials {
  pin?: string;
  password?: string;
  biometric?: boolean;
}

export interface Signature {
  signature: string;
  publicKey: string;
}
```

### Implementation Example

```typescript
// mobile-app/src/services/security.ts

import { SecurityModule } from '@wallet-ui/shared';
import * as Keychain from 'react-native-keychain';
import TouchID from 'react-native-touch-id';

export class MobileSecurityService implements SecurityModule {
  async createWallet(chain: Chain): Promise<WalletInfo> {
    // Call native security module
    const result = await NativeSecurity.createWallet(chain);
    
    // Store encrypted keys in keychain
    await Keychain.setGenericPassword(
      result.id,
      result.encryptedKey,
      { service: 'wallet-keys' }
    );
    
    return result;
  }

  async signTransaction(
    walletId: string,
    unsignedTx: UnsignedTransaction
  ): Promise<SignedTransaction> {
    // Verify biometrics if enabled
    const biometricsEnabled = await this.isBiometricsEnabled(walletId);
    
    if (biometricsEnabled) {
      await this.verifyBiometrics(walletId);
    }
    
    // Retrieve keys from secure storage
    const credentials = await Keychain.getGenericPassword({ service: 'wallet-keys' });
    
    if (!credentials) {
      throw new Error('Wallet locked');
    }
    
    // Sign transaction
    return NativeSecurity.signTransaction(credentials.password, unsignedTx);
  }

  async verifyBiometrics(walletId: string): Promise<boolean> {
    try {
      await TouchID.authenticate('Unlock wallet to sign transaction', {
        title: 'Authentication Required',
        color: '#667eea',
      });
      return true;
    } catch (error) {
      throw new Error('Biometric authentication failed');
    }
  }
  
  // ... implement other methods
}
```

### Recovery Dialog Integration

```typescript
// Integrate with night-chain-security for recovery phrase display

import { SecurityModule } from '../services/security';

const security = new SecurityModule();

async function showRecoveryPhrase(walletId: string) {
  // Request authentication
  const authenticated = await security.verifyBiometrics(walletId);
  
  if (!authenticated) {
    throw new Error('Authentication failed');
  }
  
  // Get recovery phrase
  const recoveryPhrase = await security.exportRecoveryPhrase(walletId);
  
  // Show in secure dialog (provided by night-chain-security UI)
  await showSecureDialog({
    title: 'Recovery Phrase',
    content: recoveryPhrase,
    copyButton: true,
    screenshotProtection: true,
  });
}
```

## Complete Flow Example

### Send Transaction Flow

```typescript
// 1. User enters command
const input = "send 10 ADA to addr1qx...";

// 2. Parse command
const parser = new CommandParser();
const parsed = parser.parse(input);

// 3. Check for ambiguities
if (parsed.ambiguities.length > 0) {
  showAmbiguityMessage(parsed.ambiguities);
  return;
}

// 4. Build transaction (wallet-core-engine)
const engine = new WalletEngineService();
const unsignedTx = await engine.buildTransaction(parsed.intent);

// 5. Estimate fee (wallet-core-engine)
const { fee, feeAsset } = await engine.estimateFee(parsed.intent);

// 6. Show preview to user
const preview = buildPreview(parsed.intent, fee, feeAsset);
showTransactionPreview(preview);

// 7. User confirms
await waitForUserConfirmation();

// 8. Request signing (night-chain-security)
const security = new SecurityModule();
const signedTx = await security.signTransaction(walletId, unsignedTx);

// 9. Submit transaction (wallet-core-engine)
const txHash = await engine.submitTransaction(signedTx);

// 10. Show confirmation
showSuccess(`Transaction submitted: ${txHash}`);
```

## Configuration

### Environment Variables

```bash
# Web Extension
WALLET_ENGINE_URL=http://localhost:8080
SECURITY_MODULE_URL=http://localhost:8081

# Mobile App
WALLET_ENGINE_URL=https://api.wallet.app
ENABLE_BIOMETRICS=true

# Discord Bot
DISCORD_BOT_TOKEN=your_token
WALLET_API_URL=http://localhost:8080
```

### Platform-Specific Setup

**Web Extension:**
```typescript
// background.ts
import { WalletEngineService } from './services/wallet-engine';
import { SecurityService } from './services/security';

const engine = new WalletEngineService(process.env.WALLET_ENGINE_URL);
const security = new SecurityService(process.env.SECURITY_MODULE_URL);
```

**Mobile App:**
```typescript
// App.tsx
import { NativeSecurity } from './native-modules/security';
import { WalletEngine } from './services/wallet-engine';

const security = new NativeSecurity();
const engine = new WalletEngine();
```

## Error Handling

```typescript
try {
  const signedTx = await security.signTransaction(walletId, unsignedTx);
} catch (error) {
  if (error.code === 'BIOMETRIC_FAILED') {
    showError('Biometric authentication failed', 'Try again or use PIN');
  } else if (error.code === 'WALLET_LOCKED') {
    showError('Wallet is locked', 'Unlock your wallet to continue');
  } else {
    showError('Transaction failed', 'Please try again');
  }
}
```

## Testing Integration

```typescript
// Mock implementations for testing

export class MockWalletEngine implements WalletCoreEngine {
  async buildTransaction(intent: TransactionIntent) {
    return {
      chain: intent.chain,
      txBody: 'mock_tx_body',
      inputs: [],
      outputs: [],
      fee: '0.17',
    };
  }
  
  // ... mock other methods
}

export class MockSecurity implements SecurityModule {
  async signTransaction(walletId: string, unsignedTx: UnsignedTransaction) {
    return {
      ...unsignedTx,
      witnesses: ['mock_witness'],
      txHash: 'mock_tx_hash',
    };
  }
  
  // ... mock other methods
}
```

## Deployment Checklist

- [ ] Configure wallet-core-engine endpoint URLs
- [ ] Set up night-chain-security module
- [ ] Test transaction signing flow
- [ ] Verify recovery phrase backup/restore
- [ ] Test biometric authentication (mobile)
- [ ] Validate dApp connection flow (extension)
- [ ] Set up error reporting
- [ ] Configure production API endpoints
- [ ] Test all platforms (web, iOS, Android)
- [ ] Security audit completed
