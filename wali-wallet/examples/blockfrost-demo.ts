/**
 * Blockfrost API Demo
 * 
 * This example demonstrates how to use wAli with Blockfrost for real Cardano operations
 * 
 * Setup:
 * 1. Get Blockfrost API key from https://blockfrost.io
 * 2. Set BLOCKFROST_PROJECT_ID in .env
 * 3. Run: ts-node examples/blockfrost-demo.ts
 */

import * as dotenv from 'dotenv';
import { BlockfrostAPI } from '../src/cardano/blockfrost-api';
import { CardanoWallet } from '../src/cardano/wallet';
import { WaliEngine } from '../src/wali-engine';

// Load environment variables
dotenv.config();

const BLOCKFROST_PROJECT_ID = process.env.BLOCKFROST_PROJECT_ID!;
const NETWORK = (process.env.CARDANO_NETWORK as 'mainnet' | 'testnet') || 'testnet';

// Example addresses (public, for demonstration only)
const EXAMPLE_ADDRESS = NETWORK === 'mainnet'
  ? 'addr1qxqs59lphg8g6qndelq8xwqn60ag3aeyfcp33c2kdp46a09re5df3pzwwmyq946axfcejy5n4x0y99wqpgtp2gd0k09qsgy6pz'
  : 'addr_test1qz2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3jcu5d8ps7zex2k2xt3uqxgjqnnj83ws8lhrn648jjxtwq2ytjqp';

async function main() {
  console.log('🦭 wAli Blockfrost Demo\n');
  console.log(`Network: ${NETWORK}`);
  console.log(`Example Address: ${EXAMPLE_ADDRESS}\n`);

  if (!BLOCKFROST_PROJECT_ID) {
    console.error('❌ Error: BLOCKFROST_PROJECT_ID not set in .env');
    console.error('Get your API key at https://blockfrost.io');
    process.exit(1);
  }

  // Demo 1: Direct Blockfrost API usage
  console.log('📊 Demo 1: Direct Blockfrost API Usage\n');
  await demoBlockfrostAPI();

  console.log('\n---\n');

  // Demo 2: Using CardanoWallet with Blockfrost
  console.log('💼 Demo 2: CardanoWallet with Blockfrost\n');
  await demoCardanoWallet();

  console.log('\n---\n');

  // Demo 3: Full wAli Engine with Blockfrost
  console.log('🦭 Demo 3: wAli Engine Integration\n');
  await demoWaliEngine();

  console.log('\n✨ Demo complete! 🦭');
}

async function demoBlockfrostAPI() {
  const blockfrost = new BlockfrostAPI({
    projectId: BLOCKFROST_PROJECT_ID,
    network: NETWORK,
    cacheEnabled: true,
  });

  try {
    // Health check
    console.log('🏥 Checking API health...');
    const health = await blockfrost.healthCheck();
    console.log(`   Status: ${health.healthy ? '✅ Healthy' : '❌ Unhealthy'}`);
    console.log(`   Network: ${health.network}`);

    // Get balance
    console.log('\n💰 Fetching balance...');
    const balance = await blockfrost.getBalance(EXAMPLE_ADDRESS);
    const adaAmount = (Number(balance.native.amount) / 1_000_000).toFixed(6);
    console.log(`   ADA: ${adaAmount} ₳`);
    
    if (balance.tokens && balance.tokens.length > 0) {
      console.log(`   Native Tokens: ${balance.tokens.length} different tokens`);
      balance.tokens.slice(0, 3).forEach(token => {
        console.log(`     - ${token.name}: ${token.amount}`);
      });
    }

    // Get UTXOs
    console.log('\n📦 Fetching UTXOs...');
    const utxos = await blockfrost.getUTXOs(EXAMPLE_ADDRESS);
    console.log(`   Total UTXOs: ${utxos.length}`);
    if (utxos.length > 0) {
      console.log(`   First UTXO:`);
      console.log(`     - TX: ${utxos[0].txHash.substring(0, 16)}...`);
      console.log(`     - Index: ${utxos[0].index}`);
      console.log(`     - Amount: ${(Number(utxos[0].amount) / 1_000_000).toFixed(6)} ₳`);
    }

    // Get transaction history
    console.log('\n📜 Fetching recent transactions...');
    const txs = await blockfrost.getTransactionHistory(EXAMPLE_ADDRESS, 5);
    console.log(`   Recent transactions: ${txs.length}`);
    txs.slice(0, 3).forEach((tx, i) => {
      const date = new Date(tx.timestamp).toLocaleString();
      console.log(`   ${i + 1}. ${tx.hash.substring(0, 16)}... (${date})`);
    });

    // Get latest block
    console.log('\n🔗 Fetching latest block...');
    const block = await blockfrost.getLatestBlock();
    console.log(`   Slot: ${block.slot}`);
    console.log(`   Height: ${block.height}`);
    console.log(`   Hash: ${block.hash.substring(0, 16)}...`);

    // Fee estimation
    console.log('\n💸 Estimating fees...');
    const fees = await blockfrost.estimateFees();
    console.log(`   Slow: ${(Number(fees.slow) / 1_000_000).toFixed(6)} ₳`);
    console.log(`   Medium: ${(Number(fees.medium) / 1_000_000).toFixed(6)} ₳`);
    console.log(`   Fast: ${(Number(fees.fast) / 1_000_000).toFixed(6)} ₳`);

    // ADA Handle resolution (mainnet only)
    if (NETWORK === 'mainnet') {
      console.log('\n🏷️  Resolving ADA Handle...');
      const handleAddress = await blockfrost.resolveAdaHandle('$adahandle');
      if (handleAddress) {
        console.log(`   $adahandle → ${handleAddress.substring(0, 20)}...`);
      } else {
        console.log('   Handle not found');
      }
    }

  } catch (error: any) {
    console.error('❌ Error:', error.message);
  }
}

async function demoCardanoWallet() {
  const wallet = new CardanoWallet(NETWORK, {
    projectId: BLOCKFROST_PROJECT_ID,
    network: NETWORK,
  });

  try {
    console.log('🔍 Checking Blockfrost integration...');
    console.log(`   Blockfrost available: ${wallet.isBlockfrostAvailable() ? '✅' : '❌'}`);

    console.log('\n💰 Getting balance via wallet...');
    const balance = await wallet.getBalance(EXAMPLE_ADDRESS);
    const adaAmount = (Number(balance.native.amount) / 1_000_000).toFixed(6);
    console.log(`   Balance: ${adaAmount} ₳`);

    console.log('\n📜 Getting transaction history via wallet...');
    const txs = await wallet.getTransactionHistory(EXAMPLE_ADDRESS, 3);
    console.log(`   Transactions: ${txs.length}`);

    console.log('\n📦 Getting UTXOs via wallet...');
    const utxos = await wallet.getUTXOs(EXAMPLE_ADDRESS);
    console.log(`   UTXOs: ${utxos.length}`);

  } catch (error: any) {
    console.error('❌ Error:', error.message);
  }
}

async function demoWaliEngine() {
  const wali = new WaliEngine({
    network: NETWORK,
    blockfrost: {
      projectId: BLOCKFROST_PROJECT_ID,
      network: NETWORK,
    },
  });

  try {
    console.log('🦭 Initializing wAli...');
    const initMsg = await wali.initialize();
    console.log(`   ${initMsg.emoji} ${initMsg.message}`);
    console.log(`   ${initMsg.details}`);

    console.log('\n✅ wAli is ready for mainnet operations!');
    console.log('   You can now:');
    console.log('   - Create wallets');
    console.log('   - Check balances');
    console.log('   - Build transactions');
    console.log('   - Submit to Cardano mainnet');

  } catch (error: any) {
    console.error('❌ Error:', error.message);
  }
}

// Run the demo
main().catch(console.error);
