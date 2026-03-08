# wAli Extension Icons

## Overview

This extension includes custom wAli walrus icons in three sizes:
- **16x16px** - Browser toolbar icon
- **48x48px** - Extension management page
- **128x128px** - Chrome Web Store listing

## Design

- **Background**: wAli blue (#4A90E2) with radial gradient
- **Symbol**: White "W" letter representing wAli
- **Style**: Clean, professional, recognizable at small sizes

## Location

- **Source**: `public/assets/icon-*.png`
- **Build output**: `dist/assets/icon-*.png`

## Regenerating Icons

If you need to regenerate the icons:

```bash
node create-basic-icons.js
```

This script creates PNG icons programmatically using pure Node.js (no external dependencies).

## Build Integration

The webpack configuration automatically copies icons from `public/assets/` to `dist/assets/` during the build process.

```bash
npm run build    # Production build
npm run dev      # Development build with watch mode
```

## Customization

To customize the icons:

1. Edit `create-basic-icons.js` to modify:
   - Colors (currently wAli blue #4A90E2)
   - Design (currently shows "W" letter)
   - Size/position of elements

2. Run the generator:
   ```bash
   node create-basic-icons.js
   ```

3. Rebuild the extension:
   ```bash
   npm run build
   ```

## Advanced Icons

For more sophisticated walrus icon designs:

1. Use the SVG templates in `public/assets/icon-*.svg`
2. Edit them in your favorite vector editor
3. Convert to PNG using:
   - ImageMagick: `magick icon.svg -resize 128x128 icon.png`
   - Online: https://convertio.co/svg-png/
   - Or install sharp and use the provided conversion script

## Verification

After building, verify icons are present:

```bash
# Check source icons
ls public/assets/

# Check built icons
ls dist/assets/

# Load extension in Chrome
1. Open chrome://extensions/
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `dist` folder
```

Icons should appear in the Chrome toolbar and extension management page.
