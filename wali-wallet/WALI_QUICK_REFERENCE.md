# wAli Quick Reference Card 🦭

**Your Crypto Companion Cheat Sheet**

---

## 🗣️ Talk to wAli Naturally

wAli understands natural language! Just chat normally:

### ✨ Getting Started

```
"create wallet"           → Create new wallet
"restore wallet"          → Recover existing wallet
"help"                    → Show what wAli can do
"what can you do?"        → List features
```

### 💰 Checking Balances

```
"balance"                 → Show all assets
"show balance"            → Show all assets
"how much do I have?"     → Show all assets
"show my ADA"             → Show Cardano balance
"show my BTC"             → Show Bitcoin balance
```

### 📤 Sending Crypto

```
"send 10 ADA to $alice"                    → Send to ADA handle
"send 0.001 BTC to bc1q..."                → Send Bitcoin
"transfer 5 ADA to addr1..."               → Send Cardano
"pay $bob 100 ADA"                         → Send to handle
```

### 📥 Receiving Crypto

```
"receive"                 → Show your address
"show my address"         → Show your address
"receive ADA"             → Show Cardano address
"receive BTC"             → Show Bitcoin address
```

### 📜 Transaction History

```
"show transactions"       → Recent transactions
"history"                 → Recent transactions
"show my last 10 txs"     → Last 10 transactions
```

### 🔌 DApp Connections

```
"connect to dApp"         → Start connection flow
"show connections"        → List connected dApps
"disconnect from X"       → Disconnect specific dApp
```

### 🔑 Recovery

```
"recover wallet"          → Start recovery process
"restore my wallet"       → Start recovery process
```

---

## 🎯 wAli Responses

### Message Types

| Emoji | Type      | Meaning                    |
|-------|-----------|----------------------------|
| 🦭    | Welcome   | wAli greeting              |
| ✅    | Success   | Operation completed        |
| ❌    | Error     | Something went wrong       |
| 💭    | Info      | Information or guidance    |
| ⚠️    | Warning   | Important notice           |
| ⏳    | Thinking  | Processing your request    |

### Common Messages

```
"Building your transaction..."     → wAli is working
"Here's what you're about to send" → Review transaction
"Transaction sent! 🚀"             → Success!
"Hmm, that didn't work"            → Error (with explanation)
"Let me know what you'd like"      → Waiting for input
```

---

## 🔐 Security Reminders

### ✅ Safe to Share
- Your addresses (addr1..., bc1...)
- Your Asset ID (for recovery only)
- Transaction hashes

### ❌ NEVER Share
- Your Access Key (password)
- Your recovery question answers
- Your mnemonic/seed phrase (wAli handles this)

### 🛡️ Best Practices
- Write down your Asset ID
- Memorize your Access Key
- Store them separately
- Test with small amounts first
- Double-check addresses before sending

---

## 🆘 Common Issues

### "Wallet is locked"
- **Cause**: Incorrect access key 3 times
- **Solution**: Wait 24 hours or contact support

### "Transaction failed"
- **Cause**: Insufficient balance (including fees)
- **Solution**: Check balance, ensure enough for fees

### "Can't find that address"
- **Cause**: Invalid or incorrect address
- **Solution**: Double-check the address format

### "Network error"
- **Cause**: Blockchain network slow/down
- **Solution**: Wait and try again in a few minutes

### "I forgot my Access Key"
- **Cause**: Access key not memorized/saved
- **Solution**: Unfortunately, cannot be recovered 😔
  - This is by design for security
  - You'll need to create a new wallet

---

## 💡 Pro Tips

### Faster Commands
Use quick action buttons instead of typing:
- 💰 Balance
- 📜 History  
- ⬇️ Receive
- ❓ Help

### Handles vs Addresses
```
$alice                    → Easy to remember (Cardano only)
addr1qx...               → Full address (any chain)
bc1q...                  → Bitcoin address
```

### Understanding Fees

| Chain    | Typical Fee  | Speed      |
|----------|--------------|------------|
| Cardano  | ~0.17 ADA    | ~20 sec    |
| Bitcoin  | Varies       | ~10-60 min |

wAli always shows fees before you confirm!

### Test First!
Before sending large amounts:
1. Send a small test transaction (0.1 ADA, 0.0001 BTC)
2. Confirm it arrives
3. Then send the full amount

---

## 🎓 Key Concepts

### Access Key
- Your wallet password (4-12 characters)
- Unlocks your encrypted wallet
- Cannot be reset or recovered
- Keep it secret, keep it safe!

### Asset ID
- Your wallet's identifier on Night Chain
- Like a locker number
- Needed for recovery
- Safe to write down

### Recovery Dialog
- 4 friendly questions to verify identity
- Set during wallet creation
- Required for wallet recovery
- Answer honestly!

### Mnemonic/Seed Phrase
- Master key to your wallet
- wAli handles this automatically
- Encrypted and stored on Night Chain
- You never need to see it!

---

## 🔄 Workflow Quick Guide

### Create Wallet
```
1. "create wallet"
2. Choose access key (4-12 chars)
3. Save Asset ID shown
4. Done! 🎉
```

### Send Transaction
```
1. "send X TOKEN to ADDRESS"
2. Review preview
3. "confirm"
4. Done! 🚀
```

### Recover Wallet
```
1. "recover wallet"
2. Enter Asset ID
3. Answer 4 questions
4. Enter access key
5. Welcome back! 🦭
```

---

## 📱 Platform-Specific

### Web Extension
- **Shortcut**: Ctrl+Shift+W (Cmd+Shift+W on Mac)
- **Location**: Browser toolbar icon 🦭
- **Dev Tools**: Right-click popup → Inspect

### Mobile App
- **Platforms**: iOS & Android
- **Same Commands**: Works identically
- **Notifications**: Incoming transactions

### Discord Bot
- **Prefix**: `!wali` or `@wAli`
- **Example**: `!wali balance`
- **Private**: Use DMs for security

---

## 📚 More Help

### Documentation
- **User Guide**: Full beginner guide → `WALI_USER_GUIDE.md`
- **Developer Guide**: Technical details → `WALI_DEVELOPER_GUIDE.md`
- **README**: Overview & setup → `WALI_README.md`

### In-App Help
```
"help"                    → General help
"help with recovery"      → Recovery guide
"what's an access key?"   → Concept explanation
```

### Community (Coming Soon)
- Discord: Community support
- Twitter: Updates & tips
- Email: support@wali.wallet

---

## 🎯 Example Conversations

### First-Time User
```
wAli: Hey! I'm wAli, your crypto companion! 🦭
      Ready to create your first wallet?

You:  yes

wAli: Alright! Choose an access key (4-12 characters)

You:  walrus2026

wAli: Perfect! Creating your wallet... ✨
      [shows addresses and Asset ID]
      
      Your wallet is ready! 🎉
      Save your Asset ID: asset-abc123...
```

### Sending Crypto
```
You:  send 10 ADA to $alice

wAli: Building your transaction... 🔨
      Here's what you're about to send:
      
      To: $alice (addr1qx...)
      Amount: 10 ADA
      Fee: ~0.17 ADA
      
      [Confirm] [Edit] [Cancel]

You:  confirm

wAli: Signing... ✍️
      Broadcasting... 📡
      Transaction sent! 🚀
```

### Getting Help
```
You:  I'm confused

wAli: No worries! What can I help you with?
      
      I can:
      • Show your balance
      • Send crypto
      • Receive crypto
      • View history
      • Connect to dApps
      
      What would you like to do?
```

---

<div align="center">

## 🦭 Remember

**wAli is here to make crypto simple!**

Just talk naturally and wAli will guide you.

*Your friendly crypto companion since 2026*

</div>

---

**Version 1.0.0** | **Updated**: 2026-03-02
