#!/bin/bash

# wAli Browser Extension Build Script
# Builds the production-ready extension with real wallet integration

echo "🦭 Building wAli Browser Extension..."

# Step 1: Install dependencies if needed
echo "📦 Checking dependencies..."
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Step 2: Build the extension
echo "🔨 Building extension..."
npm run build

# Step 3: Verify build
if [ -f "dist/popup.js" ] && [ -f "dist/background.js" ]; then
    echo "✅ Build successful!"
    echo ""
    echo "📁 Extension built in: $(pwd)/dist"
    echo ""
    echo "🚀 To load in Chrome:"
    echo "   1. Open chrome://extensions/"
    echo "   2. Enable 'Developer mode'"
    echo "   3. Click 'Load unpacked'"
    echo "   4. Select the 'dist' folder"
    echo ""
    echo "🦭 wAli is ready!"
else
    echo "❌ Build failed. Check errors above."
    exit 1
fi
