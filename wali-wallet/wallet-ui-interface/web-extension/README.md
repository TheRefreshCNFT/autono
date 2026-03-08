# Web Extension - Conversational Wallet

Browser extension (Chrome/Firefox) for conversational wallet interaction with natural language commands.

## Features

- 💬 **Chat-based Interface**: Natural language wallet operations
- 🔌 **dApp Integration**: CIP-30 compatible wallet provider
- 🎨 **Clean UI**: Accessible, WCAG 2.1 AA compliant design
- 🔒 **Security**: Non-custodial, keys stored locally
- ⚡ **Fast**: Instant command parsing and validation

## Installation

### Development Mode

1. **Install Dependencies**
   ```bash
   cd web-extension
   npm install
   ```

2. **Build Extension**
   ```bash
   npm run build
   # Or for development with watch:
   npm run dev
   ```

3. **Load in Browser**

   **Chrome:**
   - Navigate to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `web-extension/dist` directory

   **Firefox:**
   - Navigate to `about:debugging#/runtime/this-firefox`
   - Click "Load Temporary Add-on"
   - Select the `manifest.json` from `web-extension/dist`

## Usage

### Basic Commands

```
send 10 ADA to addr1qx...
send 50 to $feedwali
show balance
show transactions
receive
```

### dApp Integration

The extension provides a `window.cardano.conversationalwallet` API that dApps can use:

```javascript
// Connect to wallet
const wallet = await window.cardano.conversationalwallet.enable();

// Get balance
const balance = await wallet.getBalance();

// Sign transaction
const signedTx = await wallet.signTx(unsignedTx);
```

## Architecture

```
web-extension/
├── src/
│   ├── popup/           # Main UI (React)
│   │   ├── App.tsx      # Main app component
│   │   ├── components/  # Reusable components
│   │   └── App.css      # Styles
│   ├── background.ts    # Service worker (dApp requests)
│   ├── content.ts       # Content script (injector)
│   ├── injected.ts      # Page context API provider
│   └── store/           # State management (Zustand)
├── manifest.json        # Extension manifest
└── package.json
```

## Integration Points

### wallet-core-engine
- Transaction building and validation
- Fee estimation
- Transaction submission
- Balance queries

```typescript
import { WalletCoreEngine } from 'wallet-core-engine';

const engine = new WalletCoreEngine();
const { fee, feeAsset } = await engine.estimateFee(intent);
```

### night-chain-security
- Key generation and storage
- Transaction signing
- Recovery phrase management

```typescript
import { SecurityModule } from 'night-chain-security';

const security = new SecurityModule();
const signature = await security.signTransaction(tx);
```

## Components

### ChatMessage
Displays user and assistant messages with timestamps.

**Props:**
- `message: Message` - Message object with role, content, timestamp

**Accessibility:**
- Proper ARIA labels
- Semantic HTML
- Keyboard navigation

### TransactionPreviewCard
Shows transaction details before confirmation.

**Props:**
- `preview: TransactionPreview` - Transaction details
- `onConfirm: () => void` - Confirmation handler
- `onEdit: () => void` - Edit handler
- `onCancel: () => void` - Cancel handler

**Features:**
- Human-readable explanations
- Fee breakdown
- Warning display
- Send/Edit/Cancel actions

### AssetList
Displays user's assets with balances.

**Props:**
- `assets: Asset[]` - Array of assets
- `compact?: boolean` - Compact mode flag

**Features:**
- Sorted by type and balance
- Icon/badge display
- NFT metadata support

## State Management

Uses Zustand for lightweight state management:

```typescript
const {
  walletState,    // Wallet state (accounts, assets, connections)
  loading,        // Loading state
  error,          // Error state
  processCommand, // Command processor
  clearError,     // Error clearer
} = useWalletStore();
```

## Security Considerations

1. **Key Storage**: Keys stored in browser's secure storage
2. **dApp Permissions**: User approval required for all dApp connections
3. **Transaction Review**: All transactions require user confirmation
4. **Phishing Protection**: Clear dApp identification in approval flows
5. **No External Calls**: No analytics or tracking

## Browser Support

- Chrome/Chromium 88+
- Firefox 78+
- Edge 88+

## Development

### Testing
```bash
npm test
```

### Linting
```bash
npm run lint
```

### Build for Production
```bash
npm run build
```

## Troubleshooting

### Extension doesn't load
- Check manifest.json syntax
- Verify all files are built in dist/
- Check browser console for errors

### dApp connection fails
- Ensure extension is enabled
- Refresh the page
- Check dApp compatibility

### Commands not working
- Verify wallet is unlocked
- Check command syntax
- View error messages in chat
