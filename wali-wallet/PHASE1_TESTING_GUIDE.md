# Phase 1 Testing Guide - Real Wallet Integration

## Overview
This guide provides step-by-step instructions to test the Phase 1 real wallet core integration.

---

## Prerequisites

### 1. Build the Extension
```bash
cd wallet-ui-interface/web-extension
npm install
npm run build
```

Or use the build scripts:
- **Windows:** `build-extension.bat`
- **Linux/Mac:** `bash build-extension.sh`

### 2. Load in Chrome
1. Open `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select the `wallet-ui-interface/web-extension/dist` folder
5. wAli icon should appear in extensions

---

## Test Cases

### Test 1: Wallet Creation ✅

**Objective:** Verify real wallet creation with all chains

**Steps:**
1. Click wAli extension icon
2. Type: "create a new wallet"
3. Press Enter or click Send

**Expected Result:**
```
🦭 Wallet Created Successfully!

**Cardano Address:**
`addr1...` (real mainnet address starting with addr1)

**Bitcoin Addresses:**
• Legacy (P2PKH): `1...` (real address starting with 1)
• SegWit (P2WPKH): `bc1q...` (real SegWit address)
• Taproot (P2TR): `bc1p...` (real Taproot address)

**Night Chain Address:**
`night1...`

⚠️ IMPORTANT: Your recovery phrase needs to be backed up!
```

**Verify:**
- [ ] Cardano address starts with `addr1`
- [ ] Legacy Bitcoin address starts with `1`
- [ ] SegWit Bitcoin address starts with `bc1q`
- [ ] Taproot Bitcoin address starts with `bc1p`
- [ ] Night address shown
- [ ] All addresses are DIFFERENT each time you create a wallet
- [ ] User education shown for Bitcoin address types

---

### Test 2: Night Chain Backup ✅

**Objective:** Verify seed phrase encryption and Night Chain backup

**Pre-requisite:** Complete Test 1 (wallet created)

**Steps:**
1. After wallet creation, you'll see backup prompt
2. When prompted, type a 4-12 character access key
3. Example: Type "test1234"
4. Submit

**Expected Result:**
```
✅ Your seed phrase is safely stored on Night Chain!

Transaction ID: `tx_...` or asset ID

**Recovery Instructions:**
1. Keep your access key safe (you just created it)
2. You can recover your wallet anytime using the 4-line challenge
3. Never share your access key with anyone

🎉 Your wallet is now ready to use!
```

**Verify:**
- [ ] Success message shown
- [ ] Transaction/Asset ID displayed
- [ ] Access key was accepted
- [ ] Wallet state shows "isLocked: false"
- [ ] No errors in console

**Security Check:**
1. Open DevTools → Console
2. Check for any logged mnemonics or seed phrases
3. **MUST SEE:** No plaintext mnemonics in logs
4. **SHOULD SEE:** "Wiping plaintext seed phrases from memory"

---

### Test 3: Show Balance (Empty Wallet) ✅

**Objective:** Verify Blockfrost integration with empty wallet

**Pre-requisite:** Complete Test 1 & 2

**Steps:**
1. Type: "show my balance"
2. Press Enter

**Expected Result:**
```
💰 Your Balance

**Cardano:**
• 0 ADA

**Bitcoin:**
• 0 BTC
```

**Verify:**
- [ ] Balance shows 0 (wallet is new, no funds)
- [ ] No errors (Blockfrost connected successfully)
- [ ] Both Cardano and Bitcoin balances shown

**Known Issue:**
- If you see "Failed to fetch balance", check:
  - Blockfrost API key in `src/config.ts`
  - Network connectivity
  - Console for API errors

---

### Test 4: Show Receiving Addresses ✅

**Objective:** Verify address display with education

**Steps:**
1. Type: "show my address"
2. Or: "receive"
3. Or: "where can I receive funds?"

**Expected Result:**
```
🦭 Your Receiving Addresses

**Cardano:**
`addr1...` (your real address)

**Bitcoin (Choose one):**
• SegWit (Recommended): `bc1q...`
• Legacy: `1...`
• Taproot: `bc1p...`

**Night Chain:**
`night1...`

Send funds to any of these addresses. 
I recommend using SegWit for Bitcoin (lower fees).
```

**Verify:**
- [ ] All addresses shown
- [ ] Bitcoin addresses have descriptions
- [ ] SegWit marked as recommended
- [ ] User can copy addresses

---

### Test 5: Transaction History (Empty) ✅

**Objective:** Verify transaction history with no transactions

**Steps:**
1. Type: "show history"
2. Or: "show transactions"

**Expected Result:**
```
📜 Transaction History

No transactions yet. Send or receive some crypto to get started!
```

**Verify:**
- [ ] Empty state message shown
- [ ] No errors
- [ ] Blockfrost query succeeded (just returned empty array)

---

### Test 6: Balance Query with Funded Wallet 🔄

**Objective:** Verify real balance display

**Pre-requisite:** 
- Wallet created and backed up
- Fund the Cardano address with testnet ADA (or small amount of mainnet ADA)

**Steps:**
1. Send 1-10 ADA to your Cardano address from Test 1
2. Wait ~30 seconds for confirmation
3. Type: "show my balance"

**Expected Result:**
```
💰 Your Balance

**Cardano:**
• 10.00 ADA (or whatever amount you sent)

**Bitcoin:**
• 0 BTC
```

**Verify:**
- [ ] Real balance shown
- [ ] Amount matches what you sent
- [ ] Balance updates after transaction confirms

---

### Test 7: Transaction History with Funded Wallet 🔄

**Objective:** Verify real transaction history display

**Pre-requisite:** Complete Test 6 (wallet funded)

**Steps:**
1. Type: "show history"

**Expected Result:**
```
📜 Recent Transactions

**2026-03-02**
• Received 10.00 ADA
  TX: `abc123...`
```

**Verify:**
- [ ] Real transaction shown
- [ ] Correct date
- [ ] Correct amount
- [ ] Transaction hash shown (first 16 chars)

---

### Test 8: ADA Handle Resolution 🔄

**Objective:** Verify ADA handle → address resolution

**Note:** This requires an ADA handle to exist. Test with known handle.

**Steps:**
1. (Future implementation - send transaction feature)
2. Use known handle like $ada or $cardano

**Expected Result:**
- [ ] Handle resolves to real address
- [ ] Transaction can be built

---

## Security Testing

### Test S1: Memory Wiping ✅

**Objective:** Verify mnemonics are wiped from memory

**Steps:**
1. Create wallet (Test 1)
2. Complete backup (Test 2)
3. Open DevTools → Console
4. Run: `performance.memory` (if available)
5. Check console logs

**Verify:**
- [ ] No plaintext mnemonics in console
- [ ] See log: "Wiping plaintext seed phrases from memory"
- [ ] No mnemonic words visible in logs

---

### Test S2: Access Key Validation ✅

**Objective:** Verify access key requirements enforced

**Steps:**
1. Create wallet
2. Try backup with 3-character key: "abc"
3. Should fail
4. Try backup with 13-character key: "abcdefghijklm"
5. Should fail
6. Try backup with 8-character key: "test1234"
7. Should succeed

**Verify:**
- [ ] <4 chars rejected
- [ ] >12 chars rejected
- [ ] 4-12 chars accepted
- [ ] Clear error messages shown

---

### Test S3: No Local Storage of Seeds ✅

**Objective:** Verify no plaintext seeds in chrome.storage

**Steps:**
1. Create wallet + backup
2. Open DevTools → Application → Storage
3. Check chrome.storage.local

**Verify:**
- [ ] No `mnemonic` field in storage
- [ ] No `seedPhrase` field in storage
- [ ] Only encrypted data or metadata stored
- [ ] `nightBackupTxId` stored (safe, just reference)

---

## Error Handling Tests

### Test E1: Network Error (Blockfrost) 🔄

**Objective:** Verify graceful handling of API errors

**Steps:**
1. Temporarily change Blockfrost API key to invalid value
2. Try to check balance
3. Should show error

**Expected:**
```
❌ Failed to fetch balance: [error message]
```

**Verify:**
- [ ] User-friendly error shown
- [ ] No crash
- [ ] Can retry

---

### Test E2: Invalid Command ✅

**Objective:** Verify unknown commands handled

**Steps:**
1. Type: "do something random"

**Expected:**
```
Command recognized but not yet implemented.
```

**Verify:**
- [ ] No crash
- [ ] Helpful message shown

---

## Performance Tests

### Test P1: Wallet Creation Speed ✅

**Objective:** Measure wallet creation performance

**Steps:**
1. Open DevTools → Console
2. Note timestamp before "create wallet"
3. Create wallet
4. Note timestamp when addresses shown

**Expected:**
- [ ] < 5 seconds for wallet creation
- [ ] Smooth, no freezing

---

### Test P2: Balance Query Speed ✅

**Objective:** Measure Blockfrost query performance

**Steps:**
1. Time "show balance" command
2. From input to result shown

**Expected:**
- [ ] < 3 seconds for balance query
- [ ] Loading indicator shown during query

---

## Regression Tests

### Test R1: Multiple Wallets ✅

**Objective:** Verify can create multiple wallets

**Steps:**
1. Create wallet #1
2. Backup wallet #1
3. Delete wallet (if feature exists)
4. Create wallet #2
5. Verify different addresses

**Verify:**
- [ ] Wallet #2 has different addresses
- [ ] Each wallet independent

---

## Test Results Checklist

After completing all tests, verify:

- [ ] ✅ All "✅" tests passing
- [ ] 🔄 All "🔄" tests documented (may need funding)
- [ ] No console errors during normal operation
- [ ] No plaintext mnemonics in logs or storage
- [ ] Real addresses generated (not mock)
- [ ] Blockfrost integration working
- [ ] Night Chain backup flow working
- [ ] User education showing correctly

---

## Reporting Issues

### If Tests Fail

1. **Check Console:** Open DevTools, check for errors
2. **Check Network:** Verify Blockfrost API reachable
3. **Check Build:** Re-run `npm run build`
4. **Check Config:** Verify API key in `config.ts`

### Common Issues

**"Blockfrost API error"**
- Check API key in `src/config.ts`
- Verify network connectivity
- Check Blockfrost service status

**"Night Chain error"**
- Check Night Chain integration
- Verify encryption module loaded
- Check console for specific error

**"Wallet engine not initialized"**
- Check webpack build completed
- Verify all dependencies installed
- Check import paths

---

## Next Steps After Testing

Once all tests pass:

1. **Document Results:** Note any issues found
2. **Performance Metrics:** Record creation/query times
3. **User Feedback:** Get real user testing
4. **Phase 2 Readiness:** Confirm ready for transaction building

---

## 🦭 wAli Testing Complete!

When all tests pass, wAli's Phase 1 integration is SOLID and ready for Phase 2 (transactions).

**Make it WORK. Make it SECURE. Make it wAli!** ✅
