# wAli User Guide 🦭
## Your Friendly Introduction to Crypto with wAli

Welcome! If you're new to cryptocurrency or just want a simpler way to manage your digital assets, wAli is here to help. This guide will get you started in minutes.

---

## Table of Contents

1. [What is wAli?](#what-is-wali)
2. [Getting Started](#getting-started)
3. [Creating Your Wallet](#creating-your-wallet)
4. [Understanding Your Wallet](#understanding-your-wallet)
5. [Sending Crypto](#sending-crypto)
6. [Receiving Crypto](#receiving-crypto)
7. [Checking Your Balance](#checking-your-balance)
8. [Recovering Your Wallet](#recovering-your-wallet)
9. [Connecting to dApps](#connecting-to-dapps)
10. [Tips & Best Practices](#tips--best-practices)
11. [FAQ](#faq)

---

## What is wAli?

wAli is your **crypto companion**—a wallet that you can talk to naturally, like a friend. Instead of complicated forms and scary technical terms, you just chat with wAli:

- **"Show my balance"** → wAli shows what you have
- **"Send 10 ADA to $alice"** → wAli sends your crypto
- **"What can you do?"** → wAli explains features

### What Makes wAli Special?

🗣️ **Conversational**: Talk naturally, no technical jargon  
🔐 **Secure**: Military-grade encryption keeps your assets safe  
⛓️ **Multi-Chain**: Supports Cardano, Bitcoin, and more  
🦭 **Friendly**: wAli explains everything in simple terms  

---

## Getting Started

### Installation

#### Chrome Extension (Easiest)
1. Visit the Chrome Web Store
2. Search "wAli Wallet"
3. Click "Add to Chrome"
4. Click the wAli icon 🦭 in your toolbar

#### Mobile App
1. Download from App Store (iOS) or Play Store (Android)
2. Install and open wAli
3. Follow the welcome prompts

---

## Creating Your Wallet

### Step-by-Step

1. **Open wAli**  
   You'll see: "Hey! I'm wAli, your crypto companion!"

2. **Start Creation**  
   - Click "Create a new wallet"  
   - Or type: "create wallet"

3. **Choose Your Access Key**  
   wAli asks: "Choose an access key (4-12 characters)"
   
   **What's an access key?**  
   Think of it as your wallet's password. Pick something memorable but secure.
   
   ✅ Good: `walrus2026`  
   ❌ Bad: `1234` (too simple)

4. **Save Your Asset ID**  
   wAli will show you an **Asset ID** like: `asset-abc123-def456`
   
   **IMPORTANT**: Write this down! Keep it safe! You'll need it to recover your wallet.
   
   📝 **Save it like this:**
   ```
   wAli Wallet Recovery Info
   Asset ID: asset-abc123-def456
   Access Key: [don't write this down - memorize it]
   Date Created: 2026-03-02
   ```

5. **Done! 🎉**  
   wAli shows your new addresses:
   - **Cardano**: addr1qx...
   - **Bitcoin**: bc1q...
   
   You're ready to use crypto!

### What Just Happened?

1. wAli generated secret "seed phrases" (like master keys)
2. Encrypted them with your access key
3. Stored them securely on the Night blockchain
4. Created your Cardano & Bitcoin addresses
5. Wiped all temporary data for security

Your wallet is now 100% secure and only accessible by you!

---

## Understanding Your Wallet

### Your Addresses

Think of addresses like email addresses for crypto:

- **Cardano Address**: `addr1qx...` (receives ADA and Cardano tokens)
- **Bitcoin Address**: `bc1q...` (receives BTC)

You can share these addresses publicly—they're safe to give out!

### Your Asset ID

This is your wallet's **identity on Night Chain**. It's like a locker number where your encrypted wallet is stored.

⚠️ **Keep this safe!** You'll need it for recovery.

### Your Access Key

This is your **password** that unlocks your encrypted wallet.

⚠️ **Never share this!** Anyone with your Asset ID + Access Key can access your wallet.

---

## Sending Crypto

### The Easy Way

Just talk to wAli naturally:

```
You: send 10 ADA to addr1qx...

wAli: Building your transaction... ✨
      Here's what you're about to send. Look good?
      
      From: Your wallet
      To: addr1qx...
      Amount: 10 ADA
      Fee: ~0.17 ADA
      
      [Confirm] [Edit] [Cancel]

You: confirm

wAli: Transaction sent! 🚀
      Track it: abc123...
```

### Sending to ADA Handles

Cardano supports human-readable handles (like Twitter @names):

```
You: send 5 ADA to $alice

wAli: Got it! Sending 5 ADA to $alice (addr1...)
```

Much easier than copying long addresses!

### Understanding Fees

Every blockchain charges small fees for transactions:

- **Cardano**: Usually 0.15-0.20 ADA (~$0.10-0.15)
- **Bitcoin**: Varies (0.0001-0.001 BTC, depends on network)

wAli always shows you the fee before you confirm.

---

## Receiving Crypto

Super simple!

### Get Your Address

```
You: show my address

wAli: Here's your Cardano address:
      addr1qx...
      
      [Copy] [QR Code] [Share]
```

### Share It

Give this address to whoever is sending you crypto:
- Copy/paste it
- Show the QR code (they scan it)
- Send via text/email

### Wait for Confirmation

Transactions take time:
- **Cardano**: ~20 seconds (1 block)
- **Bitcoin**: ~10-60 minutes (1-6 blocks)

wAli will notify you when funds arrive! 🎉

---

## Checking Your Balance

### Quick Check

```
You: balance

wAli: You have 3 assets in your wallet:
      
      💎 Cardano (ADA): 25.5 ADA (~$20.40)
      💎 Bitcoin (BTC): 0.001 BTC (~$60.00)
      🎨 HoskyToken: 1,000,000 HOSKY
      
      [Send] [Receive] [Details]
```

### View History

```
You: show transactions

wAli: Your recent transactions:
      
      📤 Sent 10 ADA to $alice - 2 hours ago
      📥 Received 5 ADA from addr1... - Yesterday
      📤 Sent 0.0005 BTC to bc1... - 2 days ago
```

---

## Recovering Your Wallet

Lost access? No problem! As long as you have your **Asset ID** and **Access Key**, wAli can recover everything.

### Recovery Steps

1. **Start Recovery**
   ```
   You: recover wallet
   
   wAli: Let's recover your wallet! 🔍
         Enter your Asset ID:
   
   You: asset-abc123-def456
   ```

2. **Answer Questions**  
   wAli asks 4 simple questions to verify it's you:
   
   ```
   wAli: Question 1 of 4
         What's your favorite color?
   
   You: blue
   
   wAli: Question 2 of 4...
   ```
   
   *(These are examples—actual questions are from your setup)*

3. **Enter Access Key**
   ```
   wAli: Great! Now enter your access key:
   
   You: walrus2026
   
   wAli: Welcome back! Your wallet is restored. 🎉
   ```

4. **Done!**  
   All your addresses and funds are back!

### Can't Remember?

If you forgot your **Access Key** or lost your **Asset ID**, recovery is **impossible**. This is by design—no one can access your wallet without both.

💡 **Prevention**: Write down your Asset ID. Memorize your Access Key. Store them separately.

---

## Connecting to dApps

dApps (decentralized apps) are like websites that use your wallet.

### Connection Flow

```
[Website]: "Cardano dApp wants to connect"

wAli: 🔌 "Cardano NFT Marketplace" wants to connect.
      
      Permissions requested:
      • View your address
      • View your balance
      • Request transaction signatures
      
      Trust this dApp?
      
      [Approve] [Reject] [View Details]

You: approve

wAli: ✅ Connected to Cardano NFT Marketplace!
```

### Using Connected dApps

When a connected dApp wants to make a transaction:

```
[dApp]: "Buy NFT for 50 ADA"

wAli: 🖼️ Cardano NFT Marketplace wants to:
      
      Buy "Cool Walrus #123"
      Price: 50 ADA
      Royalty: 2.5 ADA
      Total: 52.5 ADA
      
      Approve this transaction?
      
      [Approve] [Reject] [Details]
```

wAli **ALWAYS** asks before signing transactions. Never auto-approve!

### Disconnect

```
You: disconnect from marketplace

wAli: 🔌 Disconnected from Cardano NFT Marketplace.
```

---

## Tips & Best Practices

### Security

✅ **DO**:
- Write down your Asset ID
- Memorize your Access Key (or store very securely)
- Keep them separate (not together)
- Use a strong Access Key (8+ characters, mix letters/numbers)
- Verify addresses before sending (double-check!)
- Start with small test transactions

❌ **DON'T**:
- Share your Access Key (NEVER!)
- Screenshot your recovery info (can be hacked)
- Store Asset ID + Access Key together (if found, wallet compromised)
- Send large amounts without testing first
- Trust unsolicited DMs asking for wallet info

### Using wAli Effectively

🗣️ **Talk naturally**: wAli understands context
```
"Send 10 ADA to $alice" ✅
"How much do I have?" ✅
"Transfer funds" ❓ (be specific!)
```

💡 **Use suggestions**: wAli often shows helpful buttons—click them!

🔍 **Ask for help**: "What can you do?" or "help" anytime

### Performance Tips

⚡ **Slow transactions?** Network might be busy. Be patient!

💰 **High fees?** (Bitcoin) Wait for network to calm down, or use "slow" fee

🔄 **Transaction stuck?** Check block explorer (wAli provides link)

---

## FAQ

### General

**Q: Is wAli free?**  
A: Yes! wAli is open-source and free. You only pay normal blockchain fees.

**Q: Can wAli access my funds?**  
A: No! Your wallet is encrypted with YOUR access key. Only you can unlock it.

**Q: Is my data collected?**  
A: Nope! Everything runs locally. Zero tracking.

**Q: Can I use wAli on multiple devices?**  
A: Yes! Just recover your wallet on each device using your Asset ID.

### Wallet Management

**Q: I forgot my Access Key. Can you reset it?**  
A: No. This is impossible by design. No one can reset it—that's what makes it secure!

**Q: Can I change my Access Key?**  
A: Not yet, but it's on the roadmap! For now, create a new wallet and transfer funds.

**Q: How many wallets can I have?**  
A: As many as you want! Each has a unique Asset ID.

### Transactions

**Q: How long do transactions take?**  
A: Cardano: ~20 seconds. Bitcoin: ~10-60 minutes. Depends on network.

**Q: Can I cancel a transaction?**  
A: Before confirming: yes. After confirming: no (it's on the blockchain).

**Q: Why was my transaction rejected?**  
A: Common reasons:
- Insufficient balance (including fees)
- Invalid address
- Network issues

wAli explains the specific reason!

### Security

**Q: Is wAli as secure as hardware wallets?**  
A: wAli uses the same encryption standards. For maximum security (large amounts), consider hardware wallets.

**Q: What if my device is stolen?**  
A: Your wallet is encrypted. Without your Access Key, it's useless to thieves!

**Q: 3-strike lockout—what happens after?**  
A: Asset is locked for 24 hours. This prevents brute-force attacks.

---

## Need More Help?

- **Chat with wAli**: Just type "help" anytime
- **Documentation**: [Full technical docs](WALI_README.md)
- **Community**: Discord (coming soon)
- **Support**: support@wali.wallet (coming soon)

---

<div align="center">

🦭 **Welcome to the wAli family!** 🦭

*Making crypto friendly, one transaction at a time*

</div>
