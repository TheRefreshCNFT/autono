# Quick Start Guide

Get the conversational wallet UI running in under 5 minutes.

## Prerequisites

- Node.js 18+ and npm
- For mobile: React Native development environment
- For Discord bot: Discord bot token

## 🚀 Web Extension (Fastest)

```bash
# 1. Navigate to project
cd wallet-ui-interface/web-extension

# 2. Install dependencies
npm install

# 3. Build extension
npm run build

# 4. Load in Chrome
# - Open chrome://extensions/
# - Enable "Developer mode"
# - Click "Load unpacked"
# - Select the web-extension/dist folder

# 5. Click the extension icon to open the wallet
```

**Try these commands:**
```
send 10 ADA to addr1qx2kd88974zk3a7...
show balance
```

---

## 📱 Mobile App

```bash
# 1. Navigate to project
cd wallet-ui-interface/mobile-app

# 2. Install dependencies
npm install

# 3. iOS setup (macOS only)
cd ios && pod install && cd ..

# 4. Run on iOS
npm run ios

# 5. Or run on Android
npm run android
```

---

## 🤖 Discord Bot

```bash
# 1. Navigate to project
cd wallet-ui-interface/discord-bot

# 2. Install dependencies
npm install

# 3. Configure bot token
cp .env.example .env
# Edit .env and add your DISCORD_BOT_TOKEN

# 4. Build and run
npm run build
npm start
```

**Test in Discord DM:**
```
send 10 ADA to $alice
show balance
```

---

## 🧪 Test the Parser

```bash
# Navigate to shared package
cd wallet-ui-interface/shared

# Install and build
npm install
npm run build

# Create test file
cat > test-parser.js << 'EOF'
const { CommandParser } = require('./dist/parser');

const parser = new CommandParser();

const commands = [
  "send 10 ADA to addr1qx...",
  "send 50 to $alice",
  "send 100",  // Ambiguous - should ask for token
  "show balance"
];

commands.forEach(cmd => {
  console.log(`\n> ${cmd}`);
  const result = parser.parse(cmd);
  console.log('Confidence:', result.confidence);
  console.log('Ambiguities:', result.ambiguities);
});
EOF

# Run test
node test-parser.js
```

---

## 🔗 Integration with Backend (Next Steps)

### 1. Implement wallet-core-engine client

```typescript
// web-extension/src/services/wallet-engine.ts
export class WalletEngineService {
  constructor(private apiUrl: string) {}

  async buildTransaction(intent: TransactionIntent) {
    const response = await fetch(`${this.apiUrl}/tx/build`, {
      method: 'POST',
      body: JSON.stringify(intent),
    });
    return response.json();
  }
}
```

### 2. Implement night-chain-security module

```typescript
// web-extension/src/services/security.ts
export class SecurityService {
  async signTransaction(walletId: string, tx: UnsignedTransaction) {
    // Call night-chain-security API
    const response = await fetch(`${this.securityUrl}/sign`, {
      method: 'POST',
      body: JSON.stringify({ walletId, tx }),
    });
    return response.json();
  }
}
```

### 3. Wire up in store

```typescript
// web-extension/src/store/wallet.ts
import { WalletEngineService } from '../services/wallet-engine';
import { SecurityService } from '../services/security';

const engine = new WalletEngineService('http://localhost:8080');
const security = new SecurityService('http://localhost:8081');

export const useWalletStore = create((set) => ({
  processCommand: async (command) => {
    const unsignedTx = await engine.buildTransaction(command.intent);
    const signedTx = await security.signTransaction('wallet-1', unsignedTx);
    const txHash = await engine.submitTransaction(signedTx);
    return { success: true, txHash };
  }
}));
```

---

## 🎨 Customization

### Change Brand Colors

**Web Extension:** `web-extension/src/popup/App.css`
```css
/* Primary color */
--primary: #667eea;  /* Change this */

/* Update in all components */
.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

**Mobile App:** `mobile-app/src/components/ChatMessage.tsx`
```typescript
const styles = StyleSheet.create({
  userBubble: {
    backgroundColor: '#667eea',  // Change this
  }
});
```

### Add New Commands

**1. Add pattern to parser** (`shared/src/parser.ts`)
```typescript
private readonly swapPatterns = [
  /^swap\s+(\d+\.?\d*)\s+(\w+)\s+for\s+(\w+)$/i,
];
```

**2. Add handler** (`shared/src/parser.ts`)
```typescript
private parseSwapCommand(input: string, ambiguities: Ambiguity[]) {
  // Implementation
}
```

**3. Update UI components** to handle new intent type

---

## 📊 Project Structure

```
wallet-ui-interface/
├── shared/              # Shared logic (parser, types, utils)
│   ├── src/
│   │   ├── parser.ts
│   │   ├── types.ts
│   │   ├── transaction-builder.ts
│   │   └── utils.ts
│   └── package.json
│
├── web-extension/       # Browser extension
│   ├── src/
│   │   ├── popup/       # React UI
│   │   ├── background.ts
│   │   ├── content.ts
│   │   └── injected.ts
│   ├── manifest.json
│   └── package.json
│
├── mobile-app/          # React Native app
│   ├── src/
│   │   ├── screens/
│   │   ├── components/
│   │   └── store/
│   ├── App.tsx
│   └── package.json
│
├── discord-bot/         # Discord integration
│   ├── src/
│   │   └── index.ts
│   └── package.json
│
├── README.md
├── INTEGRATION.md       # Backend integration guide
├── DELIVERABLES.md      # Complete deliverables checklist
└── QUICKSTART.md        # This file
```

---

## 🐛 Troubleshooting

### Web Extension

**"Failed to load extension"**
- Check that `dist/` folder exists
- Run `npm run build` first
- Verify manifest.json has no syntax errors

**"Cannot find module '@wallet-ui/shared'"**
```bash
cd ../shared
npm install
npm run build
cd ../web-extension
npm install
```

### Mobile App

**"Metro bundler won't start"**
```bash
npm start -- --reset-cache
```

**"Pod install fails" (iOS)**
```bash
cd ios
pod deintegrate
rm Podfile.lock
pod install
```

**"Build fails on Android"**
```bash
cd android
./gradlew clean
cd ..
npm run android
```

### Discord Bot

**"Invalid token"**
- Verify DISCORD_BOT_TOKEN in .env
- Check token hasn't expired
- Ensure bot has necessary permissions

**"Bot doesn't respond to DMs"**
- Check bot has MESSAGE_CONTENT intent enabled
- Verify bot is online
- Check console for error messages

---

## 📚 Next Steps

1. **Read INTEGRATION.md** for backend integration details
2. **Review DELIVERABLES.md** for complete feature list
3. **Check platform-specific READMEs** for detailed documentation
4. **Set up wallet-core-engine** API endpoint
5. **Configure night-chain-security** module
6. **Run tests** and verify functionality
7. **Deploy** to production

---

## 💡 Pro Tips

- Use `npm run dev` for auto-reload during development
- Check browser/app console for detailed error messages
- Test with small amounts first when integrating real blockchain ops
- Use mock implementations during initial testing
- Enable verbose logging for debugging

---

## 🆘 Need Help?

1. Check the relevant README in each platform directory
2. Review INTEGRATION.md for backend setup
3. Inspect browser/app console for errors
4. Verify all dependencies are installed
5. Ensure you're using Node.js 18+

---

**You're all set! Start with the web extension for the quickest demo.** 🚀
