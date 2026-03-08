# wAli Developer Setup Guide 🦭
## Building and Contributing to wAli

This guide will help you get wAli running locally for development, testing, and contributions.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Structure](#project-structure)
3. [Initial Setup](#initial-setup)
4. [Running Locally](#running-locally)
5. [Testing](#testing)
6. [Building for Production](#building-for-production)
7. [Development Workflow](#development-workflow)
8. [Architecture Deep Dive](#architecture-deep-dive)
9. [Contributing](#contributing)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required
- **Node.js**: v18+ (v22 recommended)
- **npm**: v8+ (comes with Node)
- **Git**: Latest version
- **TypeScript**: v5.9+ (installed via npm)

### Optional
- **Docker**: For Night chain local testing
- **Chrome/Firefox**: For extension development
- **Android Studio / Xcode**: For mobile development

### Check Your Setup

```bash
node --version  # Should be v18+
npm --version   # Should be v8+
git --version
```

---

## Project Structure

```
wali-wallet/
├── src/                          # Core wallet engine
│   ├── wali-engine.ts           # 🦭 Main wAli integration layer
│   ├── wallet-engine.ts         # Cardano/Bitcoin wallet ops
│   ├── cardano/                 # Cardano-specific code
│   ├── bitcoin/                 # Bitcoin-specific code
│   ├── night-chain/             # Secure storage layer
│   │   ├── integration.ts       # Night chain orchestration
│   │   ├── encryption.ts        # AES-256-GCM encryption
│   │   ├── wallet.ts            # Night wallet client
│   │   ├── recovery-dialog.ts   # Recovery system
│   │   └── access-control.ts    # 3-strike protection
│   ├── types/                   # TypeScript definitions
│   └── utils/                   # Security utilities
│
├── wallet-ui-interface/         # UI layer
│   ├── shared/                  # Shared UI logic
│   │   ├── parser.ts            # Natural language parser
│   │   ├── wali-personality.ts  # 🦭 Friendly responses
│   │   └── types.ts             # UI type definitions
│   │
│   ├── web-extension/           # Browser extension
│   │   ├── src/
│   │   │   ├── popup/
│   │   │   │   ├── WaliApp.tsx  # 🦭 Main wAli UI
│   │   │   │   └── WaliApp.css  # wAli styling
│   │   │   ├── background.ts    # Extension background script
│   │   │   ├── content.ts       # dApp injection
│   │   │   └── store/           # State management
│   │   └── manifest.json        # Extension manifest
│   │
│   ├── mobile-app/              # React Native app
│   │   └── src/
│   │       ├── screens/         # App screens
│   │       └── components/      # UI components
│   │
│   ├── discord-bot/             # Discord integration
│   │   └── src/
│   │       └── index.ts         # Bot entry point
│   │
│   └── assets/                  # Branding assets
│       ├── wali-logo.svg        # 🦭 SVG logo
│       └── wali-ascii.txt       # ASCII art
│
├── tests/                       # Test suites
├── docs/                        # Documentation
├── package.json                 # Dependencies
├── tsconfig.json               # TypeScript config
└── README.md                   # Main readme

```

---

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/wali-wallet.git
cd wali-wallet
```

### 2. Install Dependencies

#### Core Engine
```bash
npm install
```

#### Web Extension
```bash
cd wallet-ui-interface/web-extension
npm install
cd ../..
```

#### Mobile App
```bash
cd wallet-ui-interface/mobile-app
npm install
cd ../..
```

#### Discord Bot
```bash
cd wallet-ui-interface/discord-bot
npm install
cd ../..
```

### 3. Configure Environment

Create `.env` files for each component:

#### Core `.env`
```bash
# .env (root)
NETWORK=testnet

# Blockfrost API Configuration (REQUIRED for Cardano mainnet/testnet)
# Get your API key at: https://blockfrost.io
BLOCKFROST_PROJECT_ID=your_blockfrost_project_id_here
CARDANO_NETWORK=testnet  # or 'mainnet' for production

# Legacy API keys (optional, Blockfrost is preferred)
CARDANO_API_KEY=your_blockfrost_key
BITCOIN_API_KEY=your_bitcoin_api_key

# Night Chain (for secure storage)
NIGHT_CHAIN_RPC=http://localhost:8545
```

#### Extension `.env`
```bash
# wallet-ui-interface/web-extension/.env
REACT_APP_NETWORK=testnet
REACT_APP_API_URL=http://localhost:3000
```

### 4. Configure Blockfrost API (REQUIRED)

wAli uses Blockfrost to connect to the Cardano blockchain. You MUST configure this for real blockchain operations.

#### Get Your Blockfrost API Key

1. Go to [https://blockfrost.io](https://blockfrost.io)
2. Sign up for a free account
3. Create a new project (choose "testnet" for development)
4. Copy your Project ID

#### Configure in `.env`

```bash
# Required: Your Blockfrost project ID
BLOCKFROST_PROJECT_ID=testnetABC123yourprojectidhere

# Required: Network must match your Blockfrost project
CARDANO_NETWORK=testnet  # or 'mainnet' for production
```

**📚 For detailed Blockfrost setup, see [BLOCKFROST_SETUP.md](./BLOCKFROST_SETUP.md)**

### 5. Build Core Engine

```bash
npm run build
```

This compiles TypeScript to `dist/` folder.

---

## Running Locally

### Core Engine (Development)

#### Watch Mode (Auto-rebuild on changes)
```bash
npm run build -- --watch
```

#### Run Tests
```bash
npm test
```

#### Interactive REPL
```bash
ts-node
> import { WaliEngine } from './src/wali-engine'
> const wali = new WaliEngine({ network: 'testnet' })
> await wali.initialize()
> // Play with wAli!
```

### Web Extension

#### Development Mode
```bash
cd wallet-ui-interface/web-extension
npm run dev
```

This starts a dev server with hot reload.

#### Load in Browser

**Chrome:**
1. Open `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select `wallet-ui-interface/web-extension/dist/`

**Firefox:**
1. Open `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on"
3. Select `wallet-ui-interface/web-extension/dist/manifest.json`

#### Debugging
- Open extension popup
- Right-click → "Inspect"
- Use Chrome DevTools

### Mobile App

#### iOS
```bash
cd wallet-ui-interface/mobile-app
npm run ios
```

#### Android
```bash
cd wallet-ui-interface/mobile-app
npm run android
```

#### Metro Bundler
Runs automatically. Reload: Shake device → "Reload"

### Discord Bot

#### Setup Bot
1. Create bot at https://discord.com/developers
2. Copy token to `.env`
3. Enable required intents (message content, guilds)

#### Run Bot
```bash
cd wallet-ui-interface/discord-bot
npm run dev
```

---

## Testing

### Unit Tests

```bash
# All tests
npm test

# Watch mode
npm run test:watch

# Coverage report
npm run test:coverage
```

### Integration Tests

```bash
npm run test:integration
```

Tests the full wallet creation → encryption → storage → recovery flow.

### Security Tests

```bash
# Full security audit
npm run security:full

# Individual tests
npm run security:audit    # Dependency audit
npm run security:lint     # Security linting
npm run security:test     # Security test suite
npm run security:pentest  # Penetration tests
```

### End-to-End Tests

#### Extension E2E
```bash
cd wallet-ui-interface/web-extension
npm run test:e2e
```

Uses Playwright to test user workflows.

### Manual Testing Checklist

- [ ] Create new wallet
- [ ] Verify encryption (check logs - no plaintext)
- [ ] Recover wallet with correct key
- [ ] Test 3-strike lockout (fail 3 times)
- [ ] Send Cardano transaction
- [ ] Send Bitcoin transaction
- [ ] Resolve ADA handle ($handle)
- [ ] Connect to dApp
- [ ] Approve dApp transaction
- [ ] Check balance display
- [ ] View transaction history

---

## Building for Production

### Core Engine

```bash
npm run build
```

Outputs to `dist/` with:
- Compiled JavaScript
- TypeScript declarations (.d.ts)
- Source maps

### Web Extension

```bash
cd wallet-ui-interface/web-extension
npm run build
```

Creates optimized extension in `dist/`:
- Minified JS/CSS
- Optimized assets
- Production manifest

#### Package for Distribution

```bash
npm run package
```

Creates `wali-extension-v1.0.0.zip` ready for store upload.

### Mobile App

#### iOS
```bash
cd wallet-ui-interface/mobile-app
npm run build:ios
```

#### Android
```bash
npm run build:android
```

### Discord Bot

```bash
cd wallet-ui-interface/discord-bot
npm run build
npm run start
```

Deploy to your hosting platform (Railway, Heroku, AWS, etc.)

---

## Development Workflow

### Feature Development

1. **Create Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Edit code
   - Add tests
   - Update docs

3. **Test Locally**
   ```bash
   npm test
   npm run build
   ```

4. **Commit**
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

5. **Push & PR**
   ```bash
   git push origin feature/your-feature-name
   # Create PR on GitHub
   ```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Code style (formatting)
- `refactor:` Code refactoring
- `test:` Tests
- `chore:` Build/config

Examples:
```bash
feat: add Ethereum support to wAli engine
fix: resolve ADA handle lookup timeout
docs: update user guide with recovery steps
```

### Code Style

- **TypeScript strict mode**: Always
- **ESLint**: Auto-runs on commit
- **Prettier**: Auto-formats on save
- **Security linting**: Required for PRs

#### Format Code
```bash
npm run lint:fix
```

---

## Architecture Deep Dive

### wAli Engine Flow

```typescript
// 1. User talks to wAli
userInput: "send 10 ADA to $alice"

// 2. Parser converts to intent
CommandParser.parse(userInput)
→ { type: 'send', chain: 'cardano', amount: '10', to: '$alice' }

// 3. wAli Engine orchestrates
WaliEngine.buildTransaction(intent)
  → WalletEngine.buildTransaction()
    → CardanoWallet.buildTransaction()
      → CardanoAPI.resolveADAHandle('$alice')
      → CardanoAPI.getUTXOs()
      → Build unsigned transaction

// 4. User confirms
WaliEngine.sendTransaction(unsignedTx)
  → WalletEngine.signTransaction()
    → CardanoWallet.signTransaction()
  → WalletEngine.broadcastTransaction()
    → CardanoAPI.submitTransaction()

// 5. wAli responds
WaliPersonality.transaction('sent', { txHash })
→ "Transaction sent! 🚀"
```

### Security Layers

```typescript
// Layer 1: Mnemonic Generation
const mnemonic: Uint8Array = generateMnemonic()
// ✅ Typed array (not string)

// Layer 2: Immediate Encryption
const encrypted = await nightStorage.storeSeedPhrases(bundle, accessKey)
// ✅ Encrypts BEFORE any storage

// Layer 3: Verification
const verified = await nightStorage.verifyEncryptionRoundTrip()
// ✅ Confirms decryption works

// Layer 4: On-chain Storage
const txResult = await nightStorage.storeOnChain(encrypted)
// ✅ Encrypted data written to blockchain

// Layer 5: Memory Wiping
wipeMemory(mnemonic)
// ✅ Zeroes out plaintext

// Layer 6: Access Control
accessControl.recordAttempt(assetId)
// ✅ Tracks failed attempts (3-strike lockout)
```

### Night Chain Integration

```typescript
// Encryption (AES-256-GCM)
const encryptionSession = new SecureEncryptionSession(accessKey)
const encrypted = encryptionSession.encrypt(bundle)

// Storage
const txResult = await assetStorage.storeEncryptedSeedPhrases(
  walletAddress,
  encrypted,
  metadata
)

// Retrieval
const asset = await assetStorage.getEncryptedAsset(assetId)

// Decryption
const decrypted = decryptSeedPhrases(asset, accessKey)

// Access Control
const canAccess = accessControl.canAttemptAccess(assetId)
// → { allowed: true, remainingAttempts: 3 }
```

---

## Contributing

### Areas We Need Help

1. **🎨 UI/UX**: Make wAli even friendlier
2. **⛓️ New Chains**: Ethereum, Solana, etc.
3. **🔐 Security**: Audits, hardening
4. **📱 Mobile**: iOS/Android improvements
5. **📖 Docs**: Guides, tutorials, translations
6. **🧪 Testing**: More test coverage
7. **🤖 AI**: Better natural language understanding

### Contribution Checklist

- [ ] Code follows TypeScript strict mode
- [ ] All tests pass (`npm test`)
- [ ] Security tests pass (`npm run security:full`)
- [ ] ESLint passes (`npm run lint`)
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No sensitive data in commits
- [ ] PR description explains changes

### Security Contributions

**IMPORTANT**: Do NOT open public issues for vulnerabilities!

Email: security@wali.wallet (coming soon)

We'll work with you privately and credit you in the disclosure.

---

## Troubleshooting

### Build Errors

**"Cannot find module '@emurgo/cardano-serialization-lib-nodejs'"**
```bash
npm install
npm rebuild
```

**TypeScript errors after update**
```bash
rm -rf node_modules dist
npm install
npm run build
```

### Runtime Errors

**"Night wallet not initialized"**
```typescript
const wali = new WaliEngine()
await wali.initialize() // ← Don't forget this!
```

**"Encryption not configured"**
```typescript
// Make sure to provide encryption functions
const wali = new WaliEngine({
  encryptBeforeStorage: async (data) => encrypt(data),
  decryptAfterRetrieval: async (data) => decrypt(data)
})
```

### Extension Issues

**Extension doesn't load**
- Check console for errors
- Rebuild: `npm run build`
- Clear browser cache
- Reload extension

**Changes not appearing**
- Kill dev server
- Clear `dist/` folder
- Rebuild and reload

### Mobile Issues

**Metro bundler not starting**
```bash
npm start -- --reset-cache
```

**iOS build fails**
```bash
cd ios
pod install
cd ..
npm run ios
```

**Android build fails**
```bash
cd android
./gradlew clean
cd ..
npm run android
```

### Test Failures

**"Network error" in tests**
- Check internet connection
- Tests may hit real APIs (use mocks for offline)

**"Timeout" errors**
- Increase Jest timeout in `jest.config.js`

---

## Resources

### Documentation
- [wAli README](WALI_README.md)
- [User Guide](WALI_USER_GUIDE.md)
- [Security Audit](SECURITY_AUDIT_REPORT.md)
- [Integration Guide](INTEGRATION_GUIDE.md)

### External Docs
- [Cardano](https://docs.cardano.org/)
- [Bitcoin](https://developer.bitcoin.org/)
- [TypeScript](https://www.typescriptlang.org/docs/)
- [React](https://react.dev/)

### Community
- Discord (coming soon)
- GitHub Discussions
- Twitter [@wali_wallet](https://twitter.com/wali_wallet)

---

<div align="center">

🦭 **Happy coding!** 🦭

*Building the friendliest crypto wallet, one commit at a time*

</div>
