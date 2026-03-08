# wAli Beta Deployment Guide 🦭

## Quick Start - Getting wAli Running

### Step 1: Build the Extension

**Prerequisites:**
- Node.js 18.x or higher
- npm 8.x or higher

**Build Commands:**
```bash
cd wallet-ui-interface/web-extension

# Clean install (if build fails, try Docker method below)
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
npm run build
```

**If npm install fails (Windows PowerShell):**
```powershell
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item package-lock.json -ErrorAction SilentlyContinue
npm cache clean --force
npm install --force
```

**Alternative: Docker Build (Most Reliable)**
```bash
docker run -v $(pwd):/app -w /app/wallet-ui-interface/web-extension node:18-alpine sh -c "npm ci && npm run build"
```

### Step 2: Load Extension in Chrome

1. Open Chrome
2. Go to `chrome://extensions/`
3. Enable **Developer mode** (toggle in top-right)
4. Click **Load unpacked**
5. Select folder: `wallet-ui-interface/web-extension/dist/`
6. wAli extension should appear with 🦭 icon

### Step 3: Test Core Features

**Create Wallet:**
1. Click wAli extension icon
2. Type: `create wallet`
3. Save 16-word recovery challenge
4. Enter access key (4-12 characters)
5. Verify all 3 wallet addresses shown

**Check Balance:**
```
Type: balance
Expected: Shows 0 ADA (new wallet) or real balance
```

**Receive Funds:**
```
Type: receive
Expected: Modal with BTC | CARDANO | MIDNIGHT tabs
Copy Cardano address
```

**Send Transaction (CORE FEATURE):**
```
1. Type: send 1 to addr1qxy...
2. Review preview (amount, fee, total)
3. Type: confirm send <your-access-key>
4. Verify transaction sent
5. Check TX hash and explorer link
```

---

## Beta Testing Checklist

### Essential Tests (Must Pass)

- [ ] **Install & Setup**
  - [ ] Extension loads without errors
  - [ ] Create wallet flow completes
  - [ ] All 3 addresses generated (Cardano, Bitcoin x3, Midnight)
  - [ ] 16-word recovery challenge displayed
  - [ ] Access key saved

- [ ] **Send Transaction** (Critical!)
  - [ ] `send 1 to <address>` shows preview
  - [ ] Preview displays: amount, fee (0.17 ADA), total, recipient
  - [ ] `confirm send <access-key>` broadcasts transaction
  - [ ] Transaction hash displayed
  - [ ] Explorer link works
  - [ ] Balance updates after confirmation

- [ ] **ADA Handle Support**
  - [ ] `send 5 to $feedwali` resolves handle
  - [ ] Both handle and address shown in preview
  - [ ] Transaction completes successfully

- [ ] **Receive**
  - [ ] `receive` opens modal
  - [ ] 3 tabs work (BTC, CARDANO, MIDNIGHT)
  - [ ] QR codes display correctly
  - [ ] Copy buttons work

- [ ] **Balance & History**
  - [ ] `balance` shows correct ADA amount
  - [ ] `history` shows transactions or "No transactions"

- [ ] **Recovery Flow**
  - [ ] Delete and reinstall extension
  - [ ] `recover from night` opens modal
  - [ ] Enter 16-word challenge + access key
  - [ ] Wallet restored with same addresses

### Error Handling Tests

- [ ] **Invalid Commands**
  - [ ] `send abc to addr1...` → "Invalid amount" error
  - [ ] `send 1000000 to addr1...` → "Insufficient balance" error
  - [ ] `confirm send wrongkey` → "Incorrect access key" error

- [ ] **Edge Cases**
  - [ ] Cancel pending transaction with `cancel`
  - [ ] Try to send without wallet created → Error
  - [ ] Invalid ADA handle → Error
  - [ ] Network offline → Clear error message

---

## For Beta Testers

### What to Test
1. **Wallet Creation** - Does it feel easy? Clear instructions?
2. **Send Transactions** - Is the preview helpful? Fees clear?
3. **Recovery** - Can you restore your wallet easily?
4. **wAli Personality** - Is the tone friendly? Helpful?
5. **Errors** - When things go wrong, are messages clear?

### How to Report Issues

**Discord/Telegram:**
- Quick questions and real-time support
- Screenshots encouraged

**GitHub Issues:**
- Detailed bug reports
- Steps to reproduce
- Screenshots/videos
- Your Chrome version, OS

**Bug Report Template:**
```
**What happened:**
(Describe the issue)

**Expected behavior:**
(What should have happened)

**Steps to reproduce:**
1. 
2. 
3. 

**Screenshots:**
(Attach if possible)

**Environment:**
- OS: Windows/Mac/Linux
- Chrome Version: 
- Extension Version: 1.0.0-beta
```

### Safety Tips for Beta Testing

⚠️ **DO NOT USE REAL FUNDS YET** ⚠️

- Use **Cardano testnet** for testing
- Get free testnet ADA from: https://docs.cardano.org/cardano-testnet/tools/faucet
- Test recovery flow multiple times
- Save your 16-word recovery challenge + access key in multiple places

### Known Beta Limitations

1. **Night Chain Recovery** - Backend not fully connected (mock implementation)
2. **dApp Support** - Coming in v1.1 (throws "not available in beta" error)
3. **Fee Estimation** - Uses fixed 0.17 ADA (close to average, but not dynamic)
4. **No Fiat Prices** - Only crypto amounts shown
5. **Single Account** - One wallet per extension install

---

## Troubleshooting

### Extension Won't Load
```
1. Check Chrome version (must be 88+)
2. Verify Manifest V3 support
3. Check browser console for errors (F12)
4. Try rebuilding extension: npm run build
```

### Build Fails
```
1. Delete node_modules and package-lock.json
2. Run: npm cache clean --force
3. Run: npm install --legacy-peer-deps
4. If still fails, try Docker build method
5. Check Node version: node --version (need 18+)
```

### Wallet Won't Create
```
1. Check browser console (F12)
2. Verify Blockfrost API key in .env
3. Check network connection
4. Try: chrome://extensions/ → Remove extension → Reload
```

### Transaction Fails
```
1. Verify sufficient balance (amount + 0.17 ADA fee)
2. Check access key is correct
3. Verify recipient address is valid Cardano address
4. Check Blockfrost API status
```

### Recovery Doesn't Work
```
1. Verify you saved all 16 words correctly
2. Access key must match exactly (case-sensitive)
3. Check order of recovery words (Line 1, 2, 3, 4)
4. Try reinstalling extension
```

---

## Performance & Security Notes

### What wAli Does
✅ Encrypts seed phrase before Night Chain storage  
✅ Wipes sensitive data from memory after use  
✅ Never logs passwords or keys  
✅ Validates all inputs  
✅ Shows clear transaction previews  

### What wAli Doesn't Do
❌ Never sends unencrypted seeds over network  
❌ Never stores access key in plain text  
❌ Never auto-approves transactions  
❌ Never connects to unknown dApps without permission  

---

## Beta Success Criteria

### For v1.0 Release, Beta Must Show:
- [ ] **90%+ successful wallet creations**
- [ ] **95%+ successful send transactions**
- [ ] **100% successful recoveries** (when user has correct credentials)
- [ ] **< 5 critical bugs** reported
- [ ] **Positive user feedback** on UX/personality
- [ ] **No security issues** identified

### Metrics to Track:
- Time to create wallet (target: < 2 minutes)
- Time to send transaction (target: < 30 seconds)
- User confusion points (where do users ask for help?)
- Error frequency (which errors occur most?)

---

## Feedback We're Looking For

### Critical (Release Blockers)
- Security vulnerabilities
- Data loss scenarios
- Extension crashes
- Transaction failures

### Important (UX Issues)
- Confusing instructions
- Unclear error messages
- Missing features
- wAli personality improvements

### Nice-to-Have (Future Features)
- Feature requests
- UI polish suggestions
- Additional chains/tokens
- Integration ideas

---

## Support Channels

**Discord:** [Link TBD]  
**Telegram:** [Link TBD]  
**Email:** support@wali.wallet  
**GitHub Issues:** [Link TBD]  

**Response Time:**
- Critical bugs: < 24 hours
- Important issues: < 48 hours
- General feedback: < 1 week

---

## Next Steps After Beta

### v1.1 Roadmap
1. Complete Night Chain recovery backend
2. Real-time fee calculation
3. Full dApp integration (CIP-30)
4. Multi-account support
5. Fiat price display
6. Enhanced transaction history
7. Address book
8. Export transaction CSV

### v2.0 Vision
- Mobile app (React Native)
- Hardware wallet support
- Staking interface
- NFT gallery
- DeFi integrations
- Multi-chain swaps

---

## Thank You, Beta Testers! 🙏

You're helping make crypto accessible to everyone. Your feedback shapes wAli's future.

**Every bug you find** makes wAli better.  
**Every suggestion you share** makes wAli friendlier.  
**Every test you run** makes wAli more reliable.

Let's make crypto fun! 🦭💎

---

**Last Updated:** March 2, 2026  
**Version:** 1.0.0-beta  
**Status:** Ready for Beta Testing (after successful build)
