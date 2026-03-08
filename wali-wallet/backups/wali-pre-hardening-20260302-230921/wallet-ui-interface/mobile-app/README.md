# Mobile App - Conversational Wallet

Cross-platform mobile app (iOS/Android) built with React Native for conversational wallet interaction.

## Features

- 💬 **Conversational Interface**: Natural language commands
- 📱 **Native Experience**: Optimized for mobile
- 🔒 **Biometric Auth**: Face ID, Touch ID, fingerprint support
- 📊 **Asset Management**: View and manage all your tokens and NFTs
- 🌐 **Multi-chain**: Cardano and Bitcoin support
- ♿ **Accessible**: WCAG 2.1 AA compliant

## Requirements

- Node.js 18+
- React Native CLI
- Xcode (for iOS development)
- Android Studio (for Android development)

## Installation

1. **Install Dependencies**
   ```bash
   cd mobile-app
   npm install
   ```

2. **iOS Setup** (macOS only)
   ```bash
   cd ios
   pod install
   cd ..
   ```

3. **Run on iOS**
   ```bash
   npm run ios
   ```

4. **Run on Android**
   ```bash
   npm run android
   ```

## Usage

### Natural Language Commands

```
send 10 ADA to addr1qx...
send 50 to $feedwali
show balance
show my NFTs
what's my transaction history?
```

### Wallet Setup

First launch guides you through:
1. Create new wallet OR restore existing
2. Secure with PIN/biometrics
3. Backup recovery phrase

## Architecture

```
mobile-app/
├── App.tsx              # Root component
├── src/
│   ├── screens/         # Screen components
│   │   ├── ChatScreen.tsx
│   │   ├── AssetsScreen.tsx
│   │   ├── WalletSetupScreen.tsx
│   │   └── SettingsScreen.tsx
│   ├── components/      # Reusable components
│   │   ├── ChatMessage.tsx
│   │   ├── TransactionPreviewCard.tsx
│   │   └── QuickActions.tsx
│   └── store/           # State management
│       └── wallet.ts
└── package.json
```

## Screens

### ChatScreen
Main conversation interface for wallet commands.

**Features:**
- Message history
- Command input
- Transaction previews
- Quick action buttons
- Auto-scroll to latest

### AssetsScreen
View all tokens and NFTs.

**Features:**
- Sorted asset list
- Balance display
- NFT metadata
- Asset icons/images

### WalletSetupScreen
Guided wallet creation/restoration.

**Features:**
- Create new wallet
- Restore from recovery phrase
- Integration with night-chain-security
- Clear step-by-step flow

### TransactionHistoryScreen
View past transactions.

**Features:**
- Transaction list
- Status indicators
- Details view
- Search/filter

### SettingsScreen
App configuration and security.

**Features:**
- Security settings
- Currency preferences
- Language selection
- About/legal info

## Integration Points

### wallet-core-engine
Blockchain operations:
```typescript
import { WalletCoreEngine } from 'wallet-core-engine';

const engine = new WalletCoreEngine();
await engine.buildTransaction(intent);
```

### night-chain-security
Key management and signing:
```typescript
import { SecurityModule } from 'night-chain-security';

const security = new SecurityModule();
await security.createWallet();
await security.signTransaction(tx);
```

## State Management

Zustand store for app-wide state:

```typescript
const {
  walletState,    // Wallet data
  loading,        // Loading indicators
  error,          // Error handling
  processCommand, // Command processor
} = useWalletStore();
```

## Styling

- **Design System**: Custom components with consistent theming
- **Colors**: Brand-aligned palette (#667eea primary)
- **Typography**: System fonts for native feel
- **Spacing**: 4px grid system
- **Accessibility**: High contrast, large touch targets

## Security Features

1. **Biometric Authentication**: Face ID, Touch ID, fingerprint
2. **PIN Protection**: Fallback authentication
3. **Secure Storage**: Keychain (iOS) / Keystore (Android)
4. **Auto-lock**: Configurable timeout
5. **Screenshot Protection**: Sensitive screens protected

## Platform-Specific Features

### iOS
- Face ID / Touch ID
- Haptic feedback
- iOS design language
- App Store distribution

### Android
- Fingerprint / Face unlock
- Material Design
- Google Play distribution
- Android-specific permissions

## Development

### Running Tests
```bash
npm test
```

### Debugging
```bash
# React Native debugger
npm start
# Then press 'd' in terminal and select debugging option
```

### Building for Production

**iOS:**
```bash
cd ios
xcodebuild -workspace ConversationalWallet.xcworkspace \
  -scheme ConversationalWallet \
  -configuration Release
```

**Android:**
```bash
cd android
./gradlew assembleRelease
```

## Deployment

### iOS App Store
1. Configure app in App Store Connect
2. Build archive in Xcode
3. Upload via Xcode or Transporter
4. Submit for review

### Google Play Store
1. Create app in Play Console
2. Build signed APK/AAB
3. Upload to Play Console
4. Submit for review

## Troubleshooting

### Metro bundler issues
```bash
npm start -- --reset-cache
```

### iOS build fails
```bash
cd ios
pod deintegrate
pod install
```

### Android build fails
```bash
cd android
./gradlew clean
```

### Permissions not working
- Check AndroidManifest.xml (Android)
- Check Info.plist (iOS)
- Request permissions at runtime

## Performance Optimization

- **List virtualization**: FlatList for long lists
- **Image optimization**: Proper sizing and caching
- **Memoization**: React.memo for expensive components
- **Navigation**: Stack navigation for memory efficiency
- **Bundle size**: Code splitting where possible
