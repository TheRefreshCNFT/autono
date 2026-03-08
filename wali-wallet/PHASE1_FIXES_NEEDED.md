# Phase 1 Fixes Needed

## Issues Found During Testing

### 1. All 3 Wallets Must Be Created Together
**Current:** May only create one chain
**Fix Needed:** 
- Create Cardano wallet
- Create Bitcoin wallet (same seed, BIP44 derivation)
- Create Night wallet (same seed, Night derivation)
- ALL THREE created automatically on "create wallet"

### 2. Receive Modal - Multi-Chain Address Display
**Current:** Shows single address in chat
**Fix Needed:**
- "receive" command opens modal/dropdown
- Shows 3 buttons/tabs: BTC | CARDANO | MIDNIGHT
- Click each to see that chain's address
- QR code for each
- Copy button for each
- Clear labeling which chain

### 3. Night Chain 4-Line Recovery Challenge
**Current:** May not be implemented in UI
**Fix Needed:**
- After wallet created and encrypted on Night chain
- Show 4-line challenge words to user
- Format:
  ```
  Bot: [4 words]
  You: [4 words]
  Bot: [4 words]
  You: [4 words]
  ```
- User must save these 16 words (4 lines × 4 words)
- These are used to recover access if they forget access key
- Must be stored AFTER encryption verified
- Explain: "Save these 16 words - they're your recovery challenge"

### 4. Recovery Flow UI
**Current:** May show text prompt only
**Fix Needed:**
- "import wallet" → show option: "Recover from Night Chain"
- If selected: show 4-line dialog
- User enters their 4 saved lines
- System matches pattern
- If match: decrypt with access key
- Restore wallet

## Priority
🔴 **CRITICAL:** Items 1, 2, 3 must work before beta launch
🟡 **Important:** Item 4 (recovery UI polish)

## Reference
- Night chain recovery specs in: `src/night-chain/recovery-dialog.ts`
- 4-line challenge already coded, just needs UI connection
