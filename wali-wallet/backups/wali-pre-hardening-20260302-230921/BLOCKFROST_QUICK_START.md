# Blockfrost Quick Start - 5 Minutes to Mainnet 🦭

Get wAli connected to Cardano mainnet in 5 minutes!

## Step 1: Get Your API Key (2 minutes)

1. Go to **[blockfrost.io](https://blockfrost.io)**
2. Click **"Sign Up"**
3. Verify your email
4. Click **"Add Project"**
5. Choose **"Cardano Mainnet"** (or "Testnet" for testing)
6. Copy your **Project ID** (looks like: `mainnetABC123...`)

## Step 2: Configure wAli (1 minute)

Create a `.env` file in the project root:

```bash
BLOCKFROST_PROJECT_ID=mainnetABC123yourprojectidhere
CARDANO_NETWORK=mainnet
```

**⚠️ Important:** Never commit this file! (Already in `.gitignore`)

## Step 3: Install Dependencies (1 minute)

```bash
npm install
```

## Step 4: Test Connection (1 minute)

```bash
node test-blockfrost.js
```

You should see:
```
✅ SUCCESS! Blockfrost is configured correctly!
```

## Step 5: Start Building! 🚀

### Example: Check a Balance

```typescript
import { WaliEngine } from './src/wali-engine';

const wali = new WaliEngine({
  network: 'mainnet',
  blockfrost: {
    projectId: process.env.BLOCKFROST_PROJECT_ID!,
    network: 'mainnet',
  },
});

await wali.initialize();

// Get balance
const balance = await wali.getBalances({
  cardano: 'addr1...'
});

console.log(`ADA: ${balance.cardano.native.amount}`);
```

### Example: Resolve an ADA Handle

```typescript
import { CardanoWallet } from './src/cardano/wallet';

const wallet = new CardanoWallet('mainnet', {
  projectId: process.env.BLOCKFROST_PROJECT_ID!,
  network: 'mainnet',
});

const address = await wallet.resolveAdaHandle('$alice');
console.log(`$alice → ${address}`);
```

---

## 🎓 What's Next?

- **Full Setup Guide:** [BLOCKFROST_SETUP.md](./BLOCKFROST_SETUP.md)
- **Developer Guide:** [WALI_DEVELOPER_GUIDE.md](./WALI_DEVELOPER_GUIDE.md)
- **Integration Status:** [BLOCKFROST_INTEGRATION_STATUS.md](./BLOCKFROST_INTEGRATION_STATUS.md)
- **Demo Code:** [examples/blockfrost-demo.ts](./examples/blockfrost-demo.ts)

## 🆘 Troubleshooting

### "Invalid API Key"
- Check your `.env` file exists
- Verify the API key is correct
- Make sure network matches (mainnet vs testnet)

### "Rate Limit Exceeded"
- Free tier: 50,000 requests/day
- Wait a moment and retry (automatic)
- Enable caching (on by default)

### "Connection Failed"
- Check internet connection
- Verify Blockfrost status: [status.blockfrost.io](https://status.blockfrost.io)

---

## 🔐 Security Checklist

- [x] `.env` file is git-ignored
- [x] Never log API keys
- [x] Use environment variables only
- [x] Rotate keys if compromised

---

**That's it! You're ready for Cardano mainnet! 🦭⛓️**

**Questions?** Read [BLOCKFROST_SETUP.md](./BLOCKFROST_SETUP.md) for complete details.
