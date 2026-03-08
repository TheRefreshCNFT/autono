# CRITICAL FIXES REQUIRED - wAli Wallet
**Priority:** BLOCKER for Mainnet  
**Can Deploy to Testnet:** Yes (with warnings)  
**Estimated Time:** 3-5 days

---

## 🔴 CRITICAL FIX #1: Enforce Encryption Verification

**File:** `wallet-ui-interface/web-extension/src/store/wallet.ts`  
**Function:** `backupToNightChain()`  
**Line:** ~140-170

### Current Code Issue
```typescript
// Backup mnemonic to Night Chain
const backupResult = await bridge.backupToNightChain(pendingMnemonic, accessKey);

// Mnemonic is wiped immediately - NO VERIFICATION!
set({ pendingMnemonic: null });
```

### Required Fix
```typescript
// Backup mnemonic to Night Chain
const backupResult = await bridge.backupToNightChain(pendingMnemonic, accessKey);

// 🔒 CRITICAL: Verify encryption works BEFORE wiping
const verified = await bridge.verifyNightBackup(backupResult.transactionId, accessKey);
if (!verified) {
  throw new Error('❌ CRITICAL: Encryption verification failed! Backup may be corrupted. Wallet NOT wiped for safety.');
}

// ONLY wipe after successful verification
set({ pendingMnemonic: null });
```

### New Function in WalletBridge
**File:** `wallet-ui-interface/web-extension/src/wallet-bridge.ts`

```typescript
/**
 * Verify Night Chain backup can be decrypted
 * CRITICAL SAFETY CHECK - prevents permanent wallet loss
 */
async verifyNightBackup(txId: string, accessKey: string): Promise<boolean> {
  try {
    // Retrieve encrypted data from Night Chain
    const encrypted = await this.nightChain.retrieve({ assetId: txId });
    
    // Try to decrypt it
    const decrypted = await this.nightChain.decrypt(encrypted, accessKey);
    
    // Verify it contains expected structure
    const bundle = JSON.parse(decrypted);
    if (!bundle.mnemonic || !bundle.chains) {
      return false;
    }
    
    return true;
  } catch (error) {
    console.error('❌ Backup verification failed:', error);
    return false;
  }
}
```

### Test Verification
```bash
# Create wallet
# Backup to Night Chain
# Before wallet UI clears mnemonic display, check that:
# 1. Verification step executes
# 2. If verification fails, mnemonic is NOT wiped
# 3. User sees error message
# 4. Can retry backup
```

---

## 🔴 CRITICAL FIX #2: Add Automated Security Testing

**Create:** `wallet-ui-interface/web-extension/src/__tests__/security.test.ts`

```typescript
import { describe, test, expect, beforeEach, afterEach } from '@jest/globals';
import { useWalletStore } from '../store/wallet';

describe('Security: No Seed Phrase Leakage', () => {
  // BIP39 wordlist (first 50 for testing)
  const bip39SampleWords = [
    'abandon', 'ability', 'able', 'about', 'above', 'absent',
    'absorb', 'abstract', 'absurd', 'abuse', 'access', 'accident',
    // ... (add all 2048 words or sample)
  ];

  let consoleLog: any;
  let consoleError: any;
  let consoleWarn: any;
  let capturedLogs: string[] = [];

  beforeEach(() => {
    // Intercept all console output
    consoleLog = console.log;
    consoleError = console.error;
    consoleWarn = console.warn;

    console.log = (...args: any[]) => {
      capturedLogs.push(args.join(' '));
    };
    console.error = (...args: any[]) => {
      capturedLogs.push(args.join(' '));
    };
    console.warn = (...args: any[]) => {
      capturedLogs.push(' '));
    };
  });

  afterEach(() => {
    // Restore original console
    console.log = consoleLog;
    console.error = consoleError;
    console.warn = consoleWarn;
    capturedLogs = [];
  });

  test('Wallet creation does not log seed words', async () => {
    const store = useWalletStore.getState();
    
    // Create wallet (generates 24-word mnemonic)
    await store.createWallet(24);
    
    // Check all captured logs for BIP39 words
    const allLogs = capturedLogs.join(' ').toLowerCase();
    
    bip39SampleWords.forEach(word => {
      expect(allLogs).not.toContain(word);
    });
  });

  test('Night Chain backup does not log seed words', async () => {
    const store = useWalletStore.getState();
    
    await store.createWallet(24);
    await store.backupToNightChain('test1234');
    
    const allLogs = capturedLogs.join(' ').toLowerCase();
    
    bip39SampleWords.forEach(word => {
      expect(allLogs).not.toContain(word);
    });
  });

  test('Transaction signing does not log seed words', async () => {
    const store = useWalletStore.getState();
    
    await store.createWallet(24);
    await store.backupToNightChain('test1234');
    await store.buildTransactionPreview('addr1test...', '10');
    await store.sendTransaction('addr1test...', '10', 'test1234');
    
    const allLogs = capturedLogs.join(' ').toLowerCase();
    
    bip39SampleWords.forEach(word => {
      expect(allLogs).not.toContain(word);
    });
  });

  test('Error messages are sanitized', () => {
    const testError = new Error('Failed to sign tx with mnemonic: abandon ability able about');
    
    // Sanitize should remove BIP39 words
    const sanitized = sanitizeError(testError);
    
    bip39SampleWords.forEach(word => {
      expect(sanitized.message.toLowerCase()).not.toContain(word);
    });
    
    expect(sanitized.message).toContain('[REDACTED_MNEMONIC]');
  });
});

describe('Security: Memory Wiping', () => {
  test('SecureContainer wipes data', () => {
    const testData = new Uint8Array([1, 2, 3, 4, 5]);
    const container = new SecureContainer(testData);
    
    // Data accessible before wipe
    expect(container.data[0]).toBe(1);
    
    // Wipe
    container.wipe();
    
    // Data should be zeroed
    expect(testData[0]).toBe(0);
    expect(testData[4]).toBe(0);
    
    // Access after wipe should throw
    expect(() => container.data).toThrow('Attempted to access wiped secure data');
  });
});
```

### Run Tests
```bash
cd wallet-ui-interface/web-extension
npm test -- security.test.ts
```

---

## 🔴 CRITICAL FIX #3: API Rate Limiting

**File:** `wallet-ui-interface/web-extension/src/wallet-bridge.ts`  
**Add:** Rate limiter class

```typescript
/**
 * Rate limiter to prevent API abuse
 */
class APIRateLimiter {
  private lastCall: number = 0;
  private minInterval: number = 1000; // 1 second between calls
  private queue: Array<() => void> = [];
  private processing: boolean = false;

  async throttle<T>(fn: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push(async () => {
        try {
          const now = Date.now();
          const elapsed = now - this.lastCall;
          
          if (elapsed < this.minInterval) {
            await new Promise(r => setTimeout(r, this.minInterval - elapsed));
          }
          
          this.lastCall = Date.now();
          const result = await fn();
          resolve(result);
        } catch (error) {
          reject(error);
        }
      });
      
      this.processQueue();
    });
  }

  private async processQueue() {
    if (this.processing || this.queue.length === 0) return;
    
    this.processing = true;
    
    while (this.queue.length > 0) {
      const task = this.queue.shift();
      if (task) await task();
    }
    
    this.processing = false;
  }
}

// Add to WalletBridge class
export class WalletBridge {
  private rateLimiter = new APIRateLimiter();
  
  // Wrap ALL Blockfrost calls
  async getBalance(address: string): Promise<Balance> {
    return this.rateLimiter.throttle(async () => {
      const blockfrost = await this.getBlockfrostAPI();
      return await blockfrost.getBalance(address);
    });
  }

  async getTransactionHistory(address: string, page: number = 0): Promise<Transaction[]> {
    return this.rateLimiter.throttle(async () => {
      const blockfrost = await this.getBlockfrostAPI();
      return await blockfrost.getTransactionHistory(address, page);
    });
  }
  
  // Apply to ALL API calls...
}
```

### Test Verification
```bash
# Spam commands in extension
send 1 to addr1...
balance
history
balance
balance
balance

# Verify:
# 1. Commands don't execute faster than 1/second
# 2. No Blockfrost 429 (rate limit) errors
# 3. User sees "Please wait..." message if spamming
```

---

## 🔴 CRITICAL FIX #4: Complete Night Chain Recovery Backend

**File:** `src/night-chain/simple-adapter.ts`  
**Function:** `retrieveFromNightChain()`

### Current Issue
```typescript
// PLACEHOLDER - not actually querying blockchain
console.log('[WARN] Asset retrieval is simulated');
return mockData;
```

### Required Fix

**Option A: Use Night Chain API (if available)**
```typescript
async retrieveFromNightChain(recoveryPhrase: string[]): Promise<EncryptedBackup> {
  // Hash recovery phrase to deterministic asset ID
  const assetId = this.deriveAssetIdFromRecovery(recoveryPhrase);
  
  try {
    // Query Night blockchain for this asset
    const response = await fetch(`${this.nightChainEndpoint}/assets/${assetId}`, {
      headers: {
        'Authorization': `Bearer ${this.apiKey}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`Night Chain query failed: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    return {
      encryptedData: data.encrypted_content,
      nonce: data.nonce,
      salt: data.salt,
      authTag: data.auth_tag,
      assetId: data.asset_id
    };
  } catch (error) {
    throw new Error(`Failed to retrieve from Night Chain: ${error.message}`);
  }
}

/**
 * Derive deterministic asset ID from 16-word recovery phrase
 */
private deriveAssetIdFromRecovery(words: string[]): string {
  if (words.length !== 16) {
    throw new Error('Recovery phrase must be exactly 16 words');
  }
  
  const combined = words.join(' ');
  const hash = crypto.createHash('sha256').update(combined).digest('hex');
  return hash;
}
```

**Option B: Store Locally with Indexing (Temporary Solution)**
```typescript
// Store mapping: recovery-phrase-hash → Night Chain txId
interface RecoveryIndex {
  recoveryHash: string;
  txId: string;
  created: number;
}

class NightChainIndexer {
  async indexBackup(recoveryPhrase: string[], txId: string): Promise<void> {
    const hash = this.hashRecoveryPhrase(recoveryPhrase);
    const index: RecoveryIndex = {
      recoveryHash: hash,
      txId,
      created: Date.now()
    };
    
    // Store in chrome.storage or IndexedDB
    await chrome.storage.local.set({ [`recovery_${hash}`]: index });
  }

  async lookupBackup(recoveryPhrase: string[]): Promise<string | null> {
    const hash = this.hashRecoveryPhrase(recoveryPhrase);
    const result = await chrome.storage.local.get(`recovery_${hash}`);
    return result[`recovery_${hash}`]?.txId || null;
  }

  private hashRecoveryPhrase(words: string[]): string {
    return crypto.createHash('sha256').update(words.join(' ')).digest('hex');
  }
}
```

### Integration
```typescript
// In wallet creation flow, store recovery index
const { recoveryChallenge, txId } = await bridge.backupToNightChain(...);
await nightChainIndexer.indexBackup(recoveryChallenge, txId);

// In recovery flow, look up txId
const txId = await nightChainIndexer.lookupBackup(userEnteredRecoveryWords);
if (!txId) {
  throw new Error('No backup found for this recovery phrase');
}
const backup = await bridge.retrieveNightBackup(txId);
```

---

## 🟠 HIGH PRIORITY: Memory Dump Testing

**Manual Test (Chrome DevTools):**

1. **Create Wallet:**
   ```
   1. Open extension
   2. Create wallet (generates 24 words)
   3. Note first 3 words of mnemonic
   ```

2. **Backup to Night Chain:**
   ```
   1. Enter access key
   2. Complete backup
   3. Wait for "Mnemonic wiped" confirmation
   ```

3. **Take Heap Snapshot:**
   ```
   1. Open Chrome DevTools (F12)
   2. Go to "Memory" tab
   3. Select "Heap snapshot"
   4. Click "Take snapshot"
   5. Wait for capture
   ```

4. **Search for Mnemonic Words:**
   ```
   1. In snapshot, use search box (Ctrl+F)
   2. Search for first word (e.g., "abandon")
   3. Check if found:
      - If FOUND: 🔴 CRITICAL SECURITY ISSUE
      - If NOT FOUND: ✅ Memory wiped correctly
   4. Repeat for 2nd and 3rd words
   ```

5. **Document Results:**
   ```
   Create: MEMORY_DUMP_TEST_RESULTS.md
   
   ## Test 1: Wallet Creation
   - Date: 2026-03-02
   - Mnemonic words searched: [word1, word2, word3]
   - Found in heap: YES / NO
   - Verdict: PASS / FAIL
   
   ## Test 2: After Night Backup
   - Date: 2026-03-02
   - Mnemonic words searched: [word1, word2, word3]
   - Found in heap: YES / NO
   - Verdict: PASS / FAIL
   
   ## Test 3: After Transaction
   - Date: 2026-03-02
   - Mnemonic words searched: [word1, word2, word3]
   - Found in heap: YES / NO
   - Verdict: PASS / FAIL
   ```

**If ANY test FAILS:**
- DO NOT DEPLOY
- Investigate wipeMemory implementation
- Check for string copies in React state
- Verify no logging

---

## 🟠 HIGH PRIORITY: Dynamic Bitcoin Fees

**File:** `wallet-ui-interface/web-extension/src/wallet-bridge.ts`

```typescript
/**
 * Estimate Bitcoin transaction fee based on network conditions
 */
async estimateBitcoinFee(): Promise<string> {
  try {
    // Use Blockstream API for fee estimation
    const response = await fetch('https://blockstream.info/api/fee-estimates');
    const fees = await response.json();
    
    // Use "6 blocks" estimate (1 hour confirmation)
    const satPerVByte = fees['6'];
    
    // Estimate transaction size (typical P2WPKH → P2WPKH)
    const estimatedVBytes = 140; // 1 input, 2 outputs (send + change)
    
    // Calculate total fee in satoshis
    const feeSats = Math.ceil(satPerVByte * estimatedVBytes);
    
    // Convert to BTC
    const feeBTC = (feeSats / 100000000).toFixed(8);
    
    return feeBTC;
  } catch (error) {
    console.error('Failed to estimate Bitcoin fee, using fallback:', error);
    return '0.0001'; // Fallback to fixed fee
  }
}

// Use in buildTransactionPreview
const estimatedFee = chain === 'cardano' 
  ? '0.17' 
  : await this.estimateBitcoinFee();
```

---

## VERIFICATION CHECKLIST

Before marking as complete:

### Critical Fix #1: Encryption Verification
- [ ] `verifyNightBackup()` function added
- [ ] Called before wiping mnemonic
- [ ] Error handling prevents wipe on failure
- [ ] User sees clear error message
- [ ] Manual test: Backup → Verify → Success
- [ ] Manual test: Corrupt backup → Verify → Fail (mnemonic kept)

### Critical Fix #2: Automated Tests
- [ ] `security.test.ts` created
- [ ] All 4 tests passing
- [ ] BIP39 wordlist complete (2048 words)
- [ ] Console interception working
- [ ] CI/CD integration configured
- [ ] Tests run on every commit

### Critical Fix #3: Rate Limiting
- [ ] `APIRateLimiter` class added
- [ ] Applied to all Blockfrost calls
- [ ] Manual test: Spam commands → Throttled
- [ ] No 429 errors from Blockfrost
- [ ] User feedback for throttling ("Please wait...")

### Critical Fix #4: Recovery Backend
- [ ] Night Chain query implemented OR
- [ ] Local indexing implemented
- [ ] Recovery flow end-to-end tested
- [ ] Can recover wallet from 16 words + access key
- [ ] All 3 addresses restored correctly
- [ ] Balance and history restored

### High Priority: Memory Testing
- [ ] Heap snapshot captured
- [ ] 3+ mnemonic words searched
- [ ] ZERO words found in memory
- [ ] Results documented
- [ ] Re-test after any changes to security code

### High Priority: Bitcoin Fees
- [ ] `estimateBitcoinFee()` implemented
- [ ] Uses real-time network data
- [ ] Fallback to fixed fee on error
- [ ] User sees accurate fee estimate
- [ ] Transactions confirm within 1 hour

---

## DEPLOYMENT TIMELINE

### Day 1-2: Critical Fixes
- Implement #1, #2, #3, #4
- Unit tests for all new code
- Code review

### Day 3: Testing
- Run automated security tests
- Memory dump testing (manual)
- End-to-end recovery testing
- Testnet transaction testing

### Day 4: Integration
- Merge fixes
- Full regression testing
- Update documentation

### Day 5: Beta Release
- Deploy to testnet
- Beta tester onboarding
- Monitor for issues

### Post-Beta: Mainnet Prep
- Fix any beta issues
- Third-party security audit (recommended)
- Gradual mainnet rollout

---

## SUCCESS CRITERIA

✅ **All 4 critical fixes implemented**  
✅ **All automated tests passing**  
✅ **Memory dump test shows ZERO mnemonic words**  
✅ **End-to-end recovery works**  
✅ **No Blockfrost rate limit errors**  
✅ **Beta testers successfully create + recover wallets**  

**THEN and ONLY THEN: Deploy to mainnet**

---

## SUPPORT

If you need help with any fix:
1. Reference this document
2. Check `FINANCIAL_SECURITY_AUDIT.md` for detailed analysis
3. Review existing security implementations in `src/utils/security.ts`
4. Test incrementally - one fix at a time

**Remember:** This is financial software. Take the time to get it right.

🦭 **One bug = lost funds = destroyed trust**

---

**Document Created:** March 2, 2026 23:05 EST  
**Owner:** wAli Development Team  
**Reviewer:** Financial Security Audit Team
