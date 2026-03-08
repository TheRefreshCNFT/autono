# Chrome Extension Testing Instructions

## Load Extension in Chrome

### Step 1: Open Chrome Extensions Page
1. Open Google Chrome
2. Navigate to: `chrome://extensions/`
3. Enable **Developer mode** (toggle in top right)

### Step 2: Load Unpacked Extension
1. Click **Load unpacked**
2. Navigate to: `C:\Users\thisc\.easyclaw\workspace\wallet-ui-interface\web-extension\dist`
3. Select the `dist` folder
4. Click **Select Folder**

### Step 3: Verify Extension Loaded
✅ Extension should appear in the list with:
- Name: "wAli - Your Friendly Multi-Chain Wallet"
- Icon: Walrus/seal emoji 🦭
- Status: No errors

### Step 4: Test Basic Functionality
1. Click the extension icon in Chrome toolbar
2. Popup should open with wAli interface
3. Try creating a wallet
4. Verify addresses are generated

---

## Expected Behavior

### Wallet Creation
When you create a wallet, you should see:
- ✅ Cardano address (starts with `addr1...`)
- ✅ Bitcoin SegWit address (starts with `bc1q...`)
- ✅ Bitcoin Legacy address (starts with `1...`)
- ✅ Bitcoin Taproot address (starts with `bc1p...`)
- ✅ Night/Midnight address

### Balance Query
- Should connect to Blockfrost API
- Query balance for generated addresses
- Display ADA balance and tokens (if any)

### Transaction Building (if funded)
- Build transaction preview
- Show fee estimation
- Sign and broadcast (requires access key)

---

## Troubleshooting

### Common Issues

#### 1. Extension Fails to Load
**Error**: Manifest errors or missing files
**Solution**: 
```bash
cd wallet-ui-interface/web-extension
npm run build
```
Rebuild and reload.

#### 2. Popup Doesn't Open
**Error**: JavaScript errors in console
**Solution**: 
- Right-click extension icon → Inspect popup
- Check console for errors
- Verify all assets loaded correctly

#### 3. MeshJS Import Errors
**Error**: Module not found or WASM errors
**Solution**: 
- Ensure all dependencies installed: `npm install --production=false`
- Rebuild: `npm run build`
- Check webpack bundle includes MeshJS

#### 4. Blockfrost API Errors
**Error**: 403 Forbidden or Invalid API Key
**Solution**: 
- Verify API key in config: `mainnetehvvvJVoJUAz5DFJJz2L9fHZmkXlXTMP`
- Check network (mainnet vs testnet)
- Verify Blockfrost account status

---

## Testing Checklist

### Basic Functionality
- [ ] Extension loads without errors
- [ ] Popup opens
- [ ] UI renders correctly
- [ ] No console errors

### Wallet Operations
- [ ] Create wallet (24-word mnemonic)
- [ ] Display all 3 chain addresses (Cardano, Bitcoin, Night)
- [ ] Backup to Night Chain
- [ ] Display recovery challenge

### Blockchain Interactions (if funded)
- [ ] Query Cardano balance (Blockfrost)
- [ ] Query Bitcoin balance
- [ ] Display transaction history
- [ ] Build transaction preview
- [ ] Sign and broadcast transaction

### Security Features
- [ ] Mnemonic wiped from memory after backup
- [ ] Access key required for transactions
- [ ] Night Chain encryption working
- [ ] No sensitive data in console

---

## Build Information

**Build Date**: March 2, 2026  
**Build Status**: ✅ SUCCESS  
**MeshJS Version**: 1.9.0-beta.101  
**Webpack Bundle**: 3.92 MB (production)

**Key Files**:
- `dist/popup.js` - Main UI bundle
- `dist/background.js` - Service worker
- `dist/content.js` - Content script
- `dist/injected.js` - Injected script
- `dist/manifest.json` - Extension manifest
- `dist/3e5038658768716fef03.module.wasm` - Crypto WASM module

---

## Debugging Tips

### Enable Verbose Logging
In `src/cardano/wallet.ts`, set `verbose: true`:
```typescript
const txBuilder = new MeshTxBuilder({
  fetcher: this.provider,
  verbose: true, // Enable detailed logging
});
```

### Check MeshJS Provider
Verify Blockfrost provider is initialized:
```typescript
console.log('Provider:', this.provider);
console.log('Network:', this.network);
```

### Monitor Network Requests
1. Open DevTools (F12)
2. Go to Network tab
3. Filter: `blockfrost.io`
4. Verify API calls are successful

---

## Success Criteria

✅ Extension loads in Chrome without errors  
✅ Popup UI renders correctly  
✅ Wallet creation works (generates addresses)  
✅ MeshJS integration functional  
✅ Blockfrost API calls succeed  
✅ No console errors or warnings

---

**Ready for Testing!** 🎉

Load the extension and verify all functionality works as expected.
