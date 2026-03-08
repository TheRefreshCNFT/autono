#!/usr/bin/env node

/**
 * wAli Startup Script 🦭
 * Displays welcome banner and provides quick access to wAli functionality
 */

const fs = require('fs');
const path = require('path');

// Display the beautiful wAli banner
function showBanner() {
  const bannerPath = path.join(__dirname, 'wallet-ui-interface', 'assets', 'wali-banner.txt');
  
  try {
    const banner = fs.readFileSync(bannerPath, 'utf-8');
    console.log(banner);
  } catch (error) {
    // Fallback simple banner
    console.log('\n🦭 wAli - Your Friendly Crypto Companion 🦭\n');
    console.log('Making crypto simple & friendly since 2026\n');
  }
}

// Show helpful next steps
function showNextSteps() {
  console.log('╔══════════════════════════════════════════════════════════════════════╗');
  console.log('║                         🚀 Get Started                               ║');
  console.log('╚══════════════════════════════════════════════════════════════════════╝');
  console.log('');
  console.log('  📦 Build the project:');
  console.log('     npm run build');
  console.log('');
  console.log('  🧪 Run tests:');
  console.log('     npm test');
  console.log('');
  console.log('  🔍 Run integration tests:');
  console.log('     npm test src/__tests__/wali-integration.test.ts');
  console.log('');
  console.log('  🌐 Build web extension:');
  console.log('     cd wallet-ui-interface/web-extension');
  console.log('     npm install && npm run build');
  console.log('');
  console.log('  📱 Run mobile app:');
  console.log('     cd wallet-ui-interface/mobile-app');
  console.log('     npm run ios    # or npm run android');
  console.log('');
  console.log('  📖 Read documentation:');
  console.log('     • User Guide: WALI_USER_GUIDE.md');
  console.log('     • Developer Guide: WALI_DEVELOPER_GUIDE.md');
  console.log('     • Quick Reference: WALI_QUICK_REFERENCE.md');
  console.log('');
  console.log('╔══════════════════════════════════════════════════════════════════════╗');
  console.log('║                      💡 Interactive Mode                             ║');
  console.log('╚══════════════════════════════════════════════════════════════════════╝');
  console.log('');
  console.log('  Try wAli in Node REPL:');
  console.log('     node');
  console.log('     > const { WaliEngine } = require("./dist/wali-engine")');
  console.log('     > const wali = new WaliEngine({ network: "testnet" })');
  console.log('     > await wali.initialize()');
  console.log('     > // Now talk to wAli!');
  console.log('');
  console.log('╔══════════════════════════════════════════════════════════════════════╗');
  console.log('║                   🦭 Welcome to the wAli family! 🦭                  ║');
  console.log('╚══════════════════════════════════════════════════════════════════════╝');
  console.log('');
}

// Main execution
showBanner();
showNextSteps();

// Check if project is built
const distExists = fs.existsSync(path.join(__dirname, 'dist'));
if (!distExists) {
  console.log('⚠️  Note: Project not built yet. Run "npm run build" first!\n');
}

// Show current directory info
console.log(`📂 Current directory: ${__dirname}`);
console.log(`📦 Package: wali-wallet v1.0.0\n`);
