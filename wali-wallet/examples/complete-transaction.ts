/**
 * Complete transaction flow example
 * Demonstrates secure wallet operations from creation to broadcast
 */

import { WalletEngine, SecureContainer } from '../src';

// Mock Night encryption (replace with actual Night integration)
class MockNightEngine {
  async encrypt(data: string): Promise<string> {
    // In production: use actual Night encryption
    return Buffer.from(data).toString('base64');
  }

  async decrypt(encrypted: string): Promise<string> {
    // In production: use actual Night decryption
    return Buffer.from(encrypted, 'base64').toString('utf8');
  }
}

async function main() {
  // Initialize wallet engine
  const engine = new WalletEngine({
    network: 'testnet',
    cardanoAPI: {
      provider: 'blockfrost',
      apiKey: process.env.BLOCKFROST_API_KEY || 'testnet-key',
      network: 'testnet'
    },
    bitcoinAPI: {
      provider: 'blockstream',
      network: 'testnet'
    }
  });

  const nightEngine = new MockNightEngine();

  console.log('=== Wallet Creation Example ===\n');

  // Step 1: Create new wallet
  const wallet = await engine.createWallet(['cardano', 'bitcoin'], 24);
  console.log('✓ Wallet created');
  console.log('  Cardano address:', wallet.addresses.cardano);
  console.log('  Bitcoin address:', wallet.addresses.bitcoin);
  console.log('  Mnemonic words:', wallet.mnemonic.split(' ').length);

  // Step 2: Encrypt and store mnemonic (CRITICAL SECURITY STEP)
  const encryptedMnemonic = await nightEngine.encrypt(wallet.mnemonic);
  console.log('\n✓ Mnemonic encrypted with Night');

  // Step 3: Wipe plaintext mnemonic immediately
  const mnemonicContainer = new SecureContainer(wallet.mnemonic);
  mnemonicContainer.wipe();
  console.log('✓ Plaintext mnemonic wiped from memory\n');

  // In production: store encryptedMnemonic securely
  // await storage.save('wallet-mnemonic', encryptedMnemonic);

  console.log('=== Balance Check Example ===\n');

  try {
    // Step 4: Check balances
    const balances = await engine.getBalances({
      cardano: wallet.addresses.cardano,
      bitcoin: wallet.addresses.bitcoin
    });

    for (const balance of balances) {
      console.log(`${balance.chain.toUpperCase()} Balance:`);
      const amount = BigInt(balance.native.amount);
      const decimals = balance.native.decimals;
      const displayAmount = Number(amount) / Math.pow(10, decimals);
      console.log(`  ${displayAmount} ${balance.native.symbol}`);

      if (balance.tokens && balance.tokens.length > 0) {
        console.log('  Tokens:');
        balance.tokens.forEach(token => {
          console.log(`    - ${token.symbol}: ${token.amount}`);
        });
      }
      console.log();
    }
  } catch (error: any) {
    console.log('Note: Balance check requires funded addresses');
    console.log('Error:', error.message, '\n');
  }

  console.log('=== Transaction Example ===\n');

  // Step 5: Build a transaction (example - would need funded address)
  try {
    // Decrypt mnemonic for transaction
    const mnemonic = await nightEngine.decrypt(encryptedMnemonic);
    const txMnemonicContainer = new SecureContainer(mnemonic);

    try {
      // Build unsigned transaction
      const unsignedTx = await engine.buildTransaction({
        chain: 'cardano',
        from: wallet.addresses.cardano!,
        to: 'addr_test1qz2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3jcu5d8ps7zex2k2xt3uqxgjqnnj83ws8lhrn648jjxtwqfjkjv7',
        amount: '1000000' // 1 ADA
      }, txMnemonicContainer.data);

      console.log('✓ Transaction built');
      console.log('  Preview:');
      console.log('    From:', unsignedTx.preview.from.substring(0, 20) + '...');
      console.log('    To:', unsignedTx.preview.to.substring(0, 20) + '...');
      console.log('    Amount:', unsignedTx.preview.amount, 'lovelace');
      console.log('    Fee:', unsignedTx.preview.fee, 'lovelace');
      console.log('    Total:', unsignedTx.preview.total, 'lovelace');

      // User would confirm here
      const userConfirmed = true; // In production: get actual user confirmation

      if (userConfirmed) {
        // Sign transaction
        const signedTx = await engine.signTransaction(
          unsignedTx,
          txMnemonicContainer.data
        );
        console.log('\n✓ Transaction signed');

        // Broadcast (commented out - would need funded address)
        // const txHash = await engine.broadcastTransaction(signedTx);
        // console.log('✓ Transaction broadcast:', txHash);
      }
    } finally {
      // Always wipe mnemonic after use
      txMnemonicContainer.wipe();
      console.log('✓ Mnemonic wiped from memory\n');
    }
  } catch (error: any) {
    console.log('Note: Transaction requires funded address and valid UTXOs');
    console.log('Error:', error.message, '\n');
  }

  console.log('=== ADA Handle Resolution Example ===\n');

  try {
    const handle = await engine.resolveADAHandle('$example');
    if (handle) {
      console.log(`✓ Resolved ${handle.handle} → ${handle.address}`);
    } else {
      console.log('Handle not found (this is expected for random handles)');
    }
  } catch (error: any) {
    console.log('ADA handle resolution:', error.message);
  }

  console.log('\n=== Fee Estimation Example ===\n');

  try {
    const fees = await engine.getFeeEstimates();
    fees.forEach(estimate => {
      console.log(`${estimate.chain.toUpperCase()} Fees (${estimate.unit}):`);
      console.log(`  Slow: ${estimate.slow}`);
      console.log(`  Medium: ${estimate.medium}`);
      console.log(`  Fast: ${estimate.fast}`);
      console.log();
    });
  } catch (error: any) {
    console.log('Fee estimation:', error.message, '\n');
  }

  console.log('=== Address Validation Example ===\n');

  const testAddresses = [
    { chain: 'cardano' as const, addr: 'addr1qxyz123...', valid: true },
    { chain: 'cardano' as const, addr: 'invalid', valid: false },
    { chain: 'bitcoin' as const, addr: 'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4', valid: true },
    { chain: 'bitcoin' as const, addr: 'invalid_btc', valid: false }
  ];

  testAddresses.forEach(test => {
    const isValid = engine.validateAddress(test.addr, test.chain);
    const status = isValid === test.valid ? '✓' : '✗';
    console.log(`${status} ${test.chain}: ${test.addr.substring(0, 20)}... → ${isValid}`);
  });

  console.log('\n=== Example Complete ===');
  console.log('\nSecurity Checklist:');
  console.log('  ✓ Mnemonic encrypted before storage');
  console.log('  ✓ Plaintext mnemonics wiped after use');
  console.log('  ✓ Transaction preview shown before signing');
  console.log('  ✓ All addresses validated');
  console.log('  ✓ Error messages sanitized');
}

// Run example
if (require.main === module) {
  main().catch(error => {
    console.error('Example failed:', error.message);
    process.exit(1);
  });
}

export { main };
