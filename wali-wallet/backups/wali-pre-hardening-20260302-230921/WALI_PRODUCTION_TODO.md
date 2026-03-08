# wAli Production TODO - Complete Launch Checklist

## CRITICAL - WALLET CORE INTEGRATION

### 1. Wire UI → Wallet Engine → Blockfrost
- [ ] Import wallet-engine into web extension
- [ ] Connect create_wallet command to real CardanoWallet.create()
- [ ] Connect import_wallet to CardanoWallet.import()
- [ ] Generate real addresses (not mock addr1qxy...)
- [ ] Query real balances via Blockfrost API
- [ ] Query real transaction history via Blockfrost
- [ ] Handle ADA handle resolution ($handle → addr1...)

### 2. Night Chain Integration - SEED PHRASE BACKUP
- [ ] After wallet creation: trigger Night chain encryption
- [ ] Prompt user for 4-12 char access key
- [ ] Encrypt seed phrase with AES-256-GCM
- [ ] Store encrypted phrase on Night blockchain
- [ ] Verify decryption works BEFORE wiping plaintext
- [ ] Show user confirmation: "Your phrase is safely stored on-chain"
- [ ] Display recovery instructions (4-line challenge explained)
- [ ] Wipe plaintext seed from memory

### 3. Night Chain Recovery Flow
- [ ] "import wallet" → offer Night chain recovery option
- [ ] Implement 4-line challenge dialog UI
- [ ] Retrieve encrypted asset from Night chain
- [ ] Decrypt with access key
- [ ] Restore wallet from recovered phrase
- [ ] Handle incorrect access key (3-strike lockout)

### 4. Bitcoin Wallet Integration (Full Support)
- [ ] Wire Bitcoin wallet creation alongside Cardano
- [ ] Generate Legacy (P2PKH) addresses (starts with 1)
- [ ] Generate SegWit (P2WPKH) addresses (starts with bc1q)
- [ ] Generate Taproot (P2TR) addresses (starts with bc1p)
- [ ] Let user choose address type (explain differences)
- [ ] Query Bitcoin balance for all address types
- [ ] Bitcoin transaction history (all types)
- [ ] Bitcoin send transaction (support all types)
- [ ] Explain to user:
  - Legacy: Oldest, highest fees, most compatible
  - SegWit: Lower fees, better for most users
  - Taproot: Newest, lowest fees, best privacy, may not work everywhere yet

## UI/UX FIXES

### 5. Quick Action Buttons
- [ ] Make suggestion buttons execute commands directly (not insert into input)
- [ ] Remove "create a new wallet" button after wallet created
- [ ] Show context-appropriate buttons (e.g., "receive", "send", "history" after wallet exists)

### 6. Welcome Flow
- [ ] Show welcome message ONLY on first run (persist flag)
- [ ] After wallet creation: show "Welcome back!" on subsequent opens
- [ ] Don't repeat setup instructions if wallet exists

### 7. Transaction Building
- [ ] Parse "send 10 ADA to addr1..." correctly
- [ ] Parse "send 50 to $alice" and resolve handle
- [ ] Build real Cardano transaction with proper UTXOs
- [ ] Calculate accurate fees
- [ ] Show transaction preview with:
  - Recipient address
  - Amount
  - Fee
  - Total (amount + fee)
  - Warning if balance insufficient
- [ ] "Edit" button on preview
- [ ] "Cancel" button on preview
- [ ] "Send" button signs and submits transaction

### 8. Transaction Signing
- [ ] Access encrypted seed from Night chain
- [ ] Prompt for access key
- [ ] Decrypt seed phrase
- [ ] Sign transaction
- [ ] Submit to Blockfrost
- [ ] Show transaction ID (tx hash)
- [ ] Wipe decrypted seed from memory immediately

## SECURITY HARDENING

### 9. Memory Security
- [ ] Verify Uint8Array wiping works
- [ ] No seed phrases in strings (anywhere)
- [ ] No logging of sensitive data
- [ ] Clear password/access key inputs after use

### 10. Access Control
- [ ] Implement 3-strike lockout on wrong access key
- [ ] 15-minute timeout after lockout
- [ ] Session timeout (auto-lock after inactivity)
- [ ] Lock wallet on extension close/browser close option

### 11. Error Handling
- [ ] Handle network errors (Blockfrost down)
- [ ] Handle invalid addresses
- [ ] Handle insufficient balance
- [ ] Handle Night chain errors
- [ ] Show user-friendly error messages (no technical jargon)

## FEATURES - COMPLETE IMPLEMENTATION

### 12. Balance Display
- [ ] Show real ADA balance
- [ ] Show all Cardano native tokens (CNTs)
- [ ] Show token metadata (names, images)
- [ ] Show Bitcoin balance
- [ ] Calculate USD values (price API integration)
- [ ] Refresh button

### 13. Transaction History
- [ ] Fetch real Cardano transaction history
- [ ] Show sent/received with amounts
- [ ] Show timestamps
- [ ] Show transaction IDs (clickable to explorer)
- [ ] Fetch Bitcoin transaction history
- [ ] Pagination for long history

### 14. Receive Workflow
- [ ] Show real generated Cardano address
- [ ] QR code for address
- [ ] Copy button
- [ ] Show Bitcoin address separately
- [ ] Explain which address for which chain

### 15. Multi-Chain Support (3 FULL WALLETS)
- [ ] Create Cardano wallet (send/receive ADA + CNTs)
- [ ] Create Bitcoin wallet (send/receive BTC, same seed, BIP44 derivation)
- [ ] Create Night wallet (send/receive Night tokens, CIP-1852 or Night-specific derivation)
- [ ] Night wallet ALSO stores encrypted backup (dual purpose)
- [ ] Display all 3 addresses clearly
- [ ] Show balances for all 3 chains
- [ ] Transaction history for all 3 chains
- [ ] Send/receive for all 3 chains
- [ ] Switch between chains in UI (tabs or dropdown)

## STORAGE & PERSISTENCE

### 16. Chrome Storage
- [ ] Persist wallet initialized flag
- [ ] Persist encrypted wallet data (if storing locally)
- [ ] Persist user preferences
- [ ] Clear storage on "delete wallet" action

### 17. Night Chain as Primary Storage
- [ ] Store ONLY encrypted data on-chain
- [ ] No local storage of seed phrases (except temp during creation)
- [ ] Document that Night chain IS the backup

## TESTING

### 18. Real Transaction Tests
- [ ] Create wallet on testnet
- [ ] Receive testnet ADA
- [ ] Send testnet ADA
- [ ] Check balance updates
- [ ] Verify transaction appears in history

### 19. Night Chain Tests
- [ ] Create wallet → encrypt → store on Night testnet
- [ ] Delete local data
- [ ] Recover wallet from Night chain
- [ ] Verify seed phrase matches original

### 20. Error Scenario Tests
- [ ] Wrong access key (3 times → lockout)
- [ ] Insufficient balance for transaction
- [ ] Invalid recipient address
- [ ] Network offline
- [ ] Blockfrost rate limit hit

## DOCUMENTATION

### 21. User Documentation
- [ ] How to create wallet
- [ ] How to backup/recover (Night chain explanation)
- [ ] How to send funds
- [ ] How to receive funds
- [ ] Security best practices
- [ ] FAQ

### 22. Recovery Instructions
- [ ] Explain 4-line challenge clearly
- [ ] Provide example walkthrough
- [ ] Explain access key importance
- [ ] What to do if access key forgotten (unrecoverable)

## BRANDING & POLISH

### 23. Logo & Icons
- [ ] ✅ Extension icons (done)
- [ ] ✅ Chat avatar (done)
- [ ] Loading states use wAli branding
- [ ] Error states show friendly wAli messages

### 24. Copy & Messaging
- [ ] Review all wAli personality messages
- [ ] Ensure consistent tone (helpful, smart, friendly)
- [ ] No technical jargon in user-facing messages
- [ ] Clear calls-to-action

## MONETIZATION INFRASTRUCTURE

### 25. dApp Integration System
- [ ] Test dApp connection approval flow
- [ ] Verify CIP-30 provider works
- [ ] Log connection requests
- [ ] (Revenue features can launch post-beta)

### 26. Ad System
- [ ] Ad placement rendering works
- [ ] Can be disabled for beta testing
- [ ] (Revenue features can launch post-beta)

## FINAL VALIDATION

### 27. Security Audit Compliance
- [ ] Run security test suite
- [ ] Verify all CRITICAL issues fixed
- [ ] No plaintext seeds in memory
- [ ] Encryption verified
- [ ] Rate limiting handled

### 28. End-to-End Workflow Test
- [ ] Fresh install → create wallet → backup to Night → receive funds → send funds → recover wallet
- [ ] All steps work without errors
- [ ] User never sees technical errors
- [ ] Recovery works exactly as documented

### 29. Cross-Browser Testing
- [ ] Test on Chrome
- [ ] Test on Edge
- [ ] Test on Brave
- [ ] Test on Firefox (if Manifest V3 compatible)

### 30. Production Readiness Checklist
- [ ] All mock data removed
- [ ] All TODOs in code addressed
- [ ] No console.log() in production build
- [ ] Error tracking/logging configured
- [ ] Analytics ready (optional)
- [ ] Backup contact method if user has issues

## DEPLOYMENT

### 31. Build Pipeline
- [ ] Production build with minification
- [ ] Source maps for debugging
- [ ] Version number in manifest
- [ ] Update URLs in manifest (real homepage, support)

### 32. Distribution
- [ ] Package extension for Chrome Web Store
- [ ] Prepare store listing (description, screenshots)
- [ ] Privacy policy page
- [ ] Terms of service
- [ ] Support email/contact

### 33. Beta Testing
- [ ] Recruit 5-10 beta testers
- [ ] Provide clear instructions
- [ ] Collect feedback
- [ ] Bug tracking system
- [ ] Iterate based on feedback

---

## CRITICAL PATH (Must Complete Before Beta)

**Phase 1: Core Wallet (Days 1-2)**
- Items 1, 2, 5, 7, 8, 9, 12, 14, 15

**Phase 2: Night Chain Backup (Days 3-4)**
- Items 2, 3, 16, 17, 19

**Phase 3: Transactions (Days 5-6)**
- Items 7, 8, 13, 18

**Phase 4: Polish & Testing (Day 7)**
- Items 6, 11, 20, 24, 27, 28

**Phase 5: Deploy Beta (Day 8)**
- Items 29, 30, 31, 32, 33

---

## ITEMS THAT CAN WAIT (Post-Beta)

- Bitcoin full integration (item 4) - can launch Cardano-only beta
- Monetization revenue features (items 25, 26) - infrastructure ready, revenue post-launch
- Multi-language support
- Mobile app (React Native version)
- Hardware wallet integration
- Advanced features (staking, governance voting)

---

**Total Critical Items: 96**
**Completed: 2** (icons, branding)
**Remaining: 94**

**Estimated Time to Beta: 7-8 days of focused development**

Once this list is complete, wAli will be a real, working, secure, production-ready crypto wallet.
