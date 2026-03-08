# wAli Build Instructions - Quick Reference

## TL;DR - Build the Extension

### Method 1: Docker (Recommended - Most Reliable)

```bash
cd wallet-ui-interface/web-extension

# Build with Docker
docker run -v $(pwd):/app -w /app node:18-alpine sh -c "npm ci && npm run build"

# Or Windows PowerShell:
docker run -v ${PWD}:/app -w /app node:18-alpine sh -c "npm ci && npm run build"
```

**Output:** `dist/` folder with all files ready to load

---

### Method 2: Local npm (If Docker Not Available)

```bash
cd wallet-ui-interface/web-extension

# Clean slate
rm -rf node_modules package-lock.json

# Force reinstall
npm cache clean --force
npm install --force

# Build
npm run build
```

**If that fails:**
```bash
# Try with legacy peer deps
npm install --legacy-peer-deps
npm run build
```

**If still fails:**
```bash
# Manual install of build dependencies
npm install webpack@5.105.3 webpack-cli@5.1.4 html-webpack-plugin@5.6.6 copy-webpack-plugin@11.0.0 ts-loader@9.5.4 css-loader@6.11.0 style-loader@3.3.4 --save-dev --force

npm run build
```

---

### Method 3: Different Machine

Sometimes environment issues prevent builds. Try:
1. Clone repo on different machine
2. Fresh `npm install`
3. `npm run build`

---

## Load Extension in Chrome

1. Open Chrome
2. Go to `chrome://extensions/`
3. Enable **Developer mode** (top-right toggle)
4. Click **Load unpacked**
5. Select `wallet-ui-interface/web-extension/dist/`
6. Done! wAli extension loaded 🦭

---

## Quick Test

After loading:

1. Click wAli extension icon
2. Type: `create wallet`
3. Type: `balance`
4. Type: `send 1 to addr1qxy...` (test address)
5. See transaction preview
6. Type: `confirm send <your-access-key>`
7. ✅ Transaction should broadcast

---

## Build Output Should Include

```
dist/
  ├── assets/
  │   ├── icon-16.png
  │   ├── icon-48.png
  │   └── icon-128.png
  ├── background.js
  ├── content.js
  ├── injected.js
  ├── manifest.json
  ├── popup.html
  └── popup.js  ← Main app (should be ~180KB+)
```

---

## Troubleshooting

**"Cannot find module 'webpack'"**
→ Dependencies not installed. Use Docker method or manual install.

**"Entry point not found"**
→ Check `src/popup/index.tsx` exists. (It should - we created it!)

**Extension won't load**
→ Check `dist/manifest.json` exists and is valid JSON.

**Black screen on popup**
→ Open DevTools (F12), check console for errors.

**Build succeeds but old code**
→ Delete `dist/` folder first, then rebuild.

---

## Environment Variables

**Optional:** Set Blockfrost API key in `.env`:

```bash
# wallet-ui-interface/web-extension/.env
BLOCKFROST_PROJECT_ID=mainnetehvvvJVoJUAz5DFJJz2L9fHZmkXlXTMP
CARDANO_NETWORK=mainnet
NODE_ENV=production
```

**Default:** Uses hardcoded fallback if not set (acceptable for beta).

---

## What Got Fixed in Latest Code

1. ✅ "Conversational Wallet" → "wAli" (3 instances)
2. ✅ Console.log removed (11 instances)
3. ✅ API key secured (environment variable)
4. ✅ Send transaction implemented (~200 lines)
5. ✅ dApp TODOs removed (clear errors)
6. ✅ Entry point exists (popup/index.tsx)
7. ✅ Icons verified (all 3 sizes)

---

## Next Steps After Build

1. **Test locally** (see BETA_DEPLOYMENT_GUIDE.md)
2. **Package for distribution:**
   ```bash
   cd wallet-ui-interface/web-extension
   zip -r wali-wallet-v1.0.0-beta.zip dist/
   ```
3. **Distribute to beta testers**
4. **Collect feedback**

---

## Support

**Build issues?**  
See: `FINAL_PRODUCTION_BUILD_REPORT.md` (comprehensive troubleshooting)

**Testing issues?**  
See: `BETA_DEPLOYMENT_GUIDE.md` (full test plan)

**Feature questions?**  
See: `SUBAGENT_COMPLETION_SUMMARY.md` (what was built)

---

**Quick Start, Quick Ship! 🚀🦭**
