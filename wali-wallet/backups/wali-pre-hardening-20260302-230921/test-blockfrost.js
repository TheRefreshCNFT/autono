#!/usr/bin/env node

/**
 * Quick Blockfrost Connection Test
 * 
 * Run this to verify your Blockfrost API key is working
 * Usage: node test-blockfrost.js
 */

const axios = require('axios');
require('dotenv').config();

const BLOCKFROST_PROJECT_ID = process.env.BLOCKFROST_PROJECT_ID;
const CARDANO_NETWORK = process.env.CARDANO_NETWORK || 'testnet';

const BASE_URL = CARDANO_NETWORK === 'mainnet'
  ? 'https://cardano-mainnet.blockfrost.io/api/v0'
  : 'https://cardano-testnet.blockfrost.io/api/v0';

// Test address (public, no sensitive data)
const TEST_ADDRESS = CARDANO_NETWORK === 'mainnet'
  ? 'addr1qxqs59lphg8g6qndelq8xwqn60ag3aeyfcp33c2kdp46a09re5df3pzwwmyq946axfcejy5n4x0y99wqpgtp2gd0k09qsgy6pz'
  : 'addr_test1qz2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3jcu5d8ps7zex2k2xt3uqxgjqnnj83ws8lhrn648jjxtwq2ytjqp';

console.log('\n🦭 wAli Blockfrost Connection Test\n');
console.log('═'.repeat(50));

if (!BLOCKFROST_PROJECT_ID) {
  console.error('\n❌ ERROR: BLOCKFROST_PROJECT_ID not found in .env');
  console.error('\nTo fix this:');
  console.error('1. Create a .env file in the project root');
  console.error('2. Add: BLOCKFROST_PROJECT_ID=your_project_id_here');
  console.error('3. Get your key at: https://blockfrost.io\n');
  process.exit(1);
}

console.log(`\n📋 Configuration:`);
console.log(`   Network: ${CARDANO_NETWORK}`);
console.log(`   API Key: ${BLOCKFROST_PROJECT_ID.substring(0, 10)}...`);
console.log(`   Base URL: ${BASE_URL}`);
console.log(`   Test Address: ${TEST_ADDRESS.substring(0, 20)}...`);

async function testConnection() {
  console.log('\n🔍 Testing connection...\n');

  try {
    // Test 1: Health check
    console.log('1️⃣  Testing API health...');
    const healthResponse = await axios.get(`${BASE_URL}/health`, {
      headers: { 'project_id': BLOCKFROST_PROJECT_ID }
    });
    console.log('   ✅ API is responding');

    // Test 2: Get latest block
    console.log('\n2️⃣  Fetching latest block...');
    const blockResponse = await axios.get(`${BASE_URL}/blocks/latest`, {
      headers: { 'project_id': BLOCKFROST_PROJECT_ID }
    });
    console.log(`   ✅ Latest block: ${blockResponse.data.height}`);
    console.log(`   ✅ Slot: ${blockResponse.data.slot}`);

    // Test 3: Get address info
    console.log('\n3️⃣  Fetching address balance...');
    const addressResponse = await axios.get(`${BASE_URL}/addresses/${TEST_ADDRESS}`, {
      headers: { 'project_id': BLOCKFROST_PROJECT_ID }
    });
    const lovelace = addressResponse.data.amount.find(a => a.unit === 'lovelace')?.quantity || '0';
    const ada = (Number(lovelace) / 1_000_000).toFixed(6);
    console.log(`   ✅ Balance: ${ada} ₳`);

    // Test 4: Get UTXOs
    console.log('\n4️⃣  Fetching UTXOs...');
    const utxoResponse = await axios.get(`${BASE_URL}/addresses/${TEST_ADDRESS}/utxos`, {
      headers: { 'project_id': BLOCKFROST_PROJECT_ID }
    });
    console.log(`   ✅ UTXOs: ${utxoResponse.data.length}`);

    // Success!
    console.log('\n' + '═'.repeat(50));
    console.log('\n✅ SUCCESS! Blockfrost is configured correctly!\n');
    console.log('You can now:');
    console.log('  • Build the project: npm run build');
    console.log('  • Run tests: npm test');
    console.log('  • Try the demo: ts-node examples/blockfrost-demo.ts');
    console.log('\n🦭 wAli is ready for Cardano mainnet! 🎉\n');

  } catch (error) {
    console.log('\n' + '═'.repeat(50));
    console.error('\n❌ ERROR: Connection failed\n');
    
    if (error.response) {
      const status = error.response.status;
      const message = error.response.data?.message || error.response.statusText;
      
      console.error(`Status: ${status}`);
      console.error(`Message: ${message}\n`);
      
      if (status === 403) {
        console.error('💡 This usually means:');
        console.error('   - Invalid or expired API key');
        console.error('   - Wrong network (check CARDANO_NETWORK in .env)');
        console.error('\nTo fix:');
        console.error('   1. Verify your API key at https://blockfrost.io');
        console.error('   2. Make sure CARDANO_NETWORK matches your project');
        console.error('   3. Generate a new API key if needed\n');
      } else if (status === 404) {
        console.error('💡 Resource not found - check your network setting\n');
      } else if (status === 429) {
        console.error('💡 Rate limit exceeded - wait a moment and try again\n');
      }
    } else if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED') {
      console.error('💡 Network error - check your internet connection\n');
    } else {
      console.error(error.message);
      console.error('\n💡 Unexpected error - check the error above\n');
    }
    
    process.exit(1);
  }
}

testConnection();
