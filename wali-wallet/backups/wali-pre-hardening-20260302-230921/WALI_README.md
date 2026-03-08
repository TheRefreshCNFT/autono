# wAli - Your Friendly Crypto Companion 🦭

<div align="center">

![wAli Logo](wallet-ui-interface/assets/wali-logo.svg)

**Making crypto simple, secure, and friendly**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-blue)](https://www.typescriptlang.org/)
[![Security](https://img.shields.io/badge/Security-Audited-green)](SECURITY_AUDIT_REPORT.md)
[![Cardano](https://img.shields.io/badge/Cardano-Mainnet%20Ready-brightgreen)](BLOCKFROST_SETUP.md)
[![Blockfrost](https://img.shields.io/badge/Powered%20by-Blockfrost-blue)](https://blockfrost.io)

[Features](#features) • [Quick Start](#quick-start) • [Documentation](#documentation) • [Security](#security) • [Mainnet Status](#mainnet-status)

</div>

---

## 🦭 What is wAli?

wAli (pronounced "wally") is your friendly crypto wallet companion that makes managing digital assets as easy as having a conversation. No jargon, no confusion—just talk to wAli naturally and it handles the rest.

### Why a Walrus?

Walruses are social, intelligent, and protective—just like wAli! They're approachable yet strong, friendly yet secure. Plus, they're adorable 🦭

## ✨ Features

### 🗣️ Conversational Interface
- **Natural Language Commands**: "Send 10 ADA to $alice" - no complex forms
- **Friendly Guidance**: wAli explains everything in human terms
- **Smart Suggestions**: Context-aware help when you need it
- **No Jargon**: Crypto made simple

### 🔐 Military-Grade Security
- **Night Chain Integration**: Your secrets are encrypted and stored on-chain
- **AES-256-GCM Encryption**: Industry-standard security
- **Zero Plaintext Storage**: Mnemonics never touch disk unencrypted
- **3-Strike Access Control**: Protection against brute force
- **Recovery Dialog**: Friendly 4-question verification system

### ⛓️ Multi-Chain Support
- **Cardano (ADA)**: ✅ **PRODUCTION READY** - Full mainnet support via Blockfrost API
  - ADA Handle resolution ($handle)
  - Native tokens (CNTs)
  - Transaction submission
  - Real-time balance queries
- **Bitcoin (BTC)**: Native SegWit addresses
- **Night Chain**: Secure encrypted storage blockchain
- **More Coming**: Ethereum, Solana, and beyond

### 🎨 Beautiful UI
- **Web Extension**: Chrome & Firefox support
- **Mobile App**: React Native (iOS & Android)
- **Discord Bot**: Manage your wallet from Discord
- **Consistent Experience**: Same friendly wAli everywhere

### 🛡️ Privacy First
- **Local Processing**: Your data stays on your device
- **No Tracking**: We don't collect usage data
- **Open Source**: Fully auditable code
- **Self-Custodial**: You control your keys, always

## 🚀 Quick Start

### Installation

#### Chrome/Firefox Extension
```bash
cd wallet-ui-interface/web-extension
npm install
npm run build
# Load unpacked extension from dist/ folder
```

#### Mobile App
```bash
cd wallet-ui-interface/mobile-app
npm install
npm run ios    # or npm run android
```

#### Discord Bot
```bash
cd wallet-ui-interface/discord-bot
npm install
npm run build
npm start
```

### Configure Blockfrost (Required for Cardano)

Before creating a wallet, you need a Blockfrost API key:

1. **Get API Key**: Visit [blockfrost.io](https://blockfrost.io) and create a free account
2. **Create Project**: Choose "mainnet" for production or "testnet" for testing
3. **Copy Project ID**: Save your project ID
4. **Configure**: Add to `.env` file:
   ```
   BLOCKFROST_PROJECT_ID=your_project_id_here
   CARDANO_NETWORK=mainnet
   ```

**📚 Full setup guide: [BLOCKFROST_SETUP.md](./BLOCKFROST_SETUP.md)**

### Create Your First Wallet

1. **Open wAli**: Launch the extension or app
2. **Say Hello**: wAli will greet you 👋
3. **Create Wallet**: Type "create wallet" or click the suggestion
4. **Choose Access Key**: Pick a memorable 4-12 character password
5. **Save Your Info**: Write down your Asset ID (you'll need this for recovery)
6. **Done!** 🎉 You're ready to use crypto

**⚠️ MAINNET WARNING**: wAli now connects to real Cardano mainnet. Use real ADA carefully!

### Send Your First Transaction

```
You: send 10 ADA to $alice
wAli: Building your transaction... This'll just take a sec! ✨

[Shows preview]

wAli: Here's what you're about to send. Look good?

You: confirm
wAli: Transaction sent! 🚀
```

## 📖 Documentation

### Architecture

```
┌─────────────────────────────────────┐
│        UI Layer (wAli Chat)         │
│  Web Extension • Mobile • Discord   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│       wAli Engine (Core Logic)      │
│  Natural Language • Transaction Mgmt │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Wallet Engine (Crypto Ops)     │
│    Cardano • Bitcoin • Signing      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│    Night Chain (Secure Storage)     │
│   Encryption • Recovery • Access     │
└─────────────────────────────────────┘
```

### Key Components

#### wAli Engine (`src/wali-engine.ts`)
The friendly orchestrator that connects all the pieces:
- Wallet creation flow
- Natural language processing
- Friendly error messages
- Recovery management

#### Wallet Engine (`src/wallet-engine.ts`)
The crypto powerhouse:
- Multi-chain address generation
- Transaction building & signing
- Balance queries
- ADA handle resolution

#### Night Chain (`src/night-chain/`)
Your secure vault:
- AES-256-GCM encryption
- On-chain asset storage
- Recovery dialog system
- Access control (3-strike lockout)

#### UI Layer (`wallet-ui-interface/`)
Where you meet wAli:
- Command parser (natural language → structured commands)
- Personality engine (friendly responses)
- Platform-specific UI (web, mobile, Discord)

### API Examples

#### Create Wallet
```typescript
import { WaliEngine } from './src/wali-engine';

const wali = new WaliEngine({ network: 'testnet' });
await wali.initialize();

const result = await wali.createWallet(
  'my-access-key',
  ['cardano', 'bitcoin']
);

console.log('Your addresses:', result.addresses);
console.log('Recovery info:', result.recoveryInstructions);
```

#### Send Transaction
```typescript
const txRequest = {
  chain: 'cardano',
  from: 'addr1...',
  to: '$alice',  // ADA handle
  amount: '10000000'  // 10 ADA in lovelace
};

const unsigned = await wali.buildTransaction(txRequest, mnemonic);
const result = await wali.sendTransaction(unsigned, mnemonic);

console.log('Transaction sent:', result.txHash);
```

#### Recover Wallet
```typescript
const { challengeId } = await wali.startRecovery('asset-id-123');

// Answer 4 questions
wali.submitRecoveryInput(challengeId, 'answer1');
wali.submitRecoveryInput(challengeId, 'answer2');
wali.submitRecoveryInput(challengeId, 'answer3');
wali.submitRecoveryInput(challengeId, 'answer4');

// Unlock with access key
const { addresses } = await wali.completeRecovery(challengeId, 'my-access-key');
```

## 🔒 Security

### Audited & Tested
- ✅ Security audit completed ([report](SECURITY_AUDIT_REPORT.md))
- ✅ Penetration testing performed
- ✅ No critical vulnerabilities
- ✅ Memory wiping verified
- ✅ Encryption round-trip tested

### Security Features
1. **No Plaintext Storage**: Mnemonics are NEVER written to disk unencrypted
2. **Memory Wiping**: Sensitive data is zeroed out after use
3. **Encryption First**: All storage operations encrypt before writing
4. **Access Control**: 3-strike lockout prevents brute force
5. **Recovery Dialog**: Human-friendly verification system
6. **Sanitized Errors**: No sensitive data in error messages

### Responsible Disclosure
Found a security issue? Please email: security@wali.wallet (coming soon)

Do NOT open a public issue for security vulnerabilities.

## 🧪 Testing

### Run All Tests
```bash
npm test
```

### Security Tests
```bash
npm run security:full
```

### Integration Tests
```bash
npm run test:integration
```

### Coverage Report
```bash
npm run test:coverage
```

## 🗺️ Roadmap

### Version 1.0 (Current) ✅
- [x] Cardano & Bitcoin support
- [x] **Cardano Mainnet via Blockfrost API** 🎉
- [x] Night Chain integration
- [x] Web extension UI
- [x] Natural language parser
- [x] Recovery system
- [x] Access control
- [x] Real-time balance queries
- [x] Transaction submission
- [x] ADA Handle resolution

### Version 1.1 (Next)
- [ ] Hardware wallet support (Ledger, Trezor)
- [ ] NFT gallery
- [ ] Token swaps (DEX integration)
- [ ] Address book
- [ ] Transaction notes

### Version 2.0 (Future)
- [ ] Ethereum support
- [ ] Solana support
- [ ] DeFi dashboard
- [ ] Portfolio analytics
- [ ] Multi-signature wallets
- [ ] Social recovery

## 🌐 Mainnet Status

### ✅ Production Ready - Cardano Mainnet

wAli is now **live on Cardano mainnet** via Blockfrost API!

**What Works:**
- ✅ Real ADA balance queries
- ✅ Native token (CNT) support
- ✅ Transaction building and submission
- ✅ ADA Handle resolution ($handle → address)
- ✅ UTXO retrieval
- ✅ Transaction history
- ✅ Fee estimation
- ✅ Asset metadata fetching

**Security Features:**
- ✅ API key protection (never logged or exposed)
- ✅ Automatic retry with exponential backoff
- ✅ Rate limiting protection
- ✅ Response caching to reduce API calls
- ✅ Network error handling
- ✅ User confirmation for mainnet transactions

**Important Notes:**
- 🔴 **This is REAL money** - Transactions on mainnet use real ADA
- ✅ Tested on testnet first
- ✅ Full integration tests included
- ⚠️ Always verify transaction details before confirming
- 📚 Read [BLOCKFROST_SETUP.md](./BLOCKFROST_SETUP.md) for complete setup

**Rate Limits (Blockfrost Free Tier):**
- 50,000 requests/day
- 10 requests/second
- Automatic retry on rate limit
- Built-in caching reduces API calls

**Get Started:**
1. Get free Blockfrost API key at [blockfrost.io](https://blockfrost.io)
2. Configure in `.env`: `BLOCKFROST_PROJECT_ID=your_key`
3. Set network: `CARDANO_NETWORK=mainnet`
4. Start building! 🦭

## 🤝 Contributing

We'd love your help making wAli even friendlier!

### Development Setup
```bash
git clone https://github.com/your-org/wali-wallet
cd wali-wallet
npm install
npm run build
npm test
```

### Guidelines
- Keep the code friendly (comments, clear names)
- Maintain security (no shortcuts!)
- Test thoroughly
- Update docs
- Follow the walrus way 🦭

### Code Style
- TypeScript strict mode
- ESLint rules enforced
- Prettier formatting
- Security linting

## 📜 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- **Cardano Community**: For the amazing blockchain
- **Bitcoin Community**: For pioneering cryptocurrency
- **Night/Midnight**: For secure privacy-preserving tech
- **Our Users**: For trusting wAli with your crypto
- **Walruses**: For being adorable 🦭

## 📞 Support

- **Documentation**: [Read the docs](docs/)
- **Discord**: [Join our community](https://discord.gg/wali) (coming soon)
- **Twitter**: [@wali_wallet](https://twitter.com/wali_wallet) (coming soon)
- **Email**: support@wali.wallet (coming soon)

---

<div align="center">

**Made with ❤️ by the wAli team**

🦭 Stay friendly, stay secure 🦭

</div>
