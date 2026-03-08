/**
 * Blockfrost Integration Tests
 * Tests real Blockfrost API interactions (use with caution on mainnet)
 */

import { BlockfrostAPI } from '../cardano/blockfrost-api';
import { CardanoWallet } from '../cardano/wallet';
import * as dotenv from 'dotenv';

// Load environment variables
// Note: Create a .env file with BLOCKFROST_PROJECT_ID for tests
const envResult = dotenv.config();

// Test configuration
const BLOCKFROST_PROJECT_ID = process.env.BLOCKFROST_PROJECT_ID || '';
const TEST_NETWORK = (process.env.CARDANO_NETWORK as 'mainnet' | 'testnet') || 'testnet';

// Known test addresses (public, no private keys)
const TEST_ADDRESSES = {
  mainnet: 'addr1qxqs59lphg8g6qndelq8xwqn60ag3aeyfcp33c2kdp46a09re5df3pzwwmyq946axfcejy5n4x0y99wqpgtp2gd0k09qsgy6pz',
  testnet: 'addr_test1qz2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3jcu5d8ps7zex2k2xt3uqxgjqnnj83ws8lhrn648jjxtwq2ytjqp',
};

// ADA Handle for testing (public)
const TEST_ADA_HANDLE = '$adahandle'; // Replace with a known handle if testing on mainnet

describe('Blockfrost API Integration', () => {
  let blockfrost: BlockfrostAPI;
  let testAddress: string;

  beforeAll(() => {
    if (!BLOCKFROST_PROJECT_ID) {
      console.warn('⚠️  BLOCKFROST_PROJECT_ID not set. Skipping integration tests.');
      console.warn('Set BLOCKFROST_PROJECT_ID in .env to run these tests.');
    }

    testAddress = TEST_ADDRESSES[TEST_NETWORK];

    blockfrost = new BlockfrostAPI({
      projectId: BLOCKFROST_PROJECT_ID,
      network: TEST_NETWORK,
      maxRetries: 2,
      retryDelayMs: 500,
      cacheEnabled: true,
    });
  });

  describe('Health Check', () => {
    test('should verify API connectivity', async () => {
      if (!BLOCKFROST_PROJECT_ID) {
        return; // Skip if no API key
      }

      const health = await blockfrost.healthCheck();
      expect(health.network).toBe(TEST_NETWORK);
      // Note: health.healthy may be false if using free tier
    }, 15000);
  });

  describe('Balance Queries', () => {
    test('should fetch balance for a valid address', async () => {
      if (!BLOCKFROST_PROJECT_ID) {
        return;
      }

      const balance = await blockfrost.getBalance(testAddress);

      expect(balance).toBeDefined();
      expect(balance.chain).toBe('cardano');
      expect(balance.address).toBe(testAddress);
      expect(balance.native).toBeDefined();
      expect(balance.native.symbol).toBe('ADA');
      expect(balance.native.decimals).toBe(6);
      expect(typeof balance.native.amount).toBe('string');
    }, 15000);

    test('should handle invalid address gracefully', async () => {
      if (!BLOCKFROST_PROJECT_ID) {
        return;
      }

      await expect(
        blockfrost.getBalance('invalid_address')
      ).rejects.toThrow();
    }, 15000);
  });

  describe('UTXO Retrieval', () => {
    test('should fetch UTXOs for an address', async () => {
      if (!BLOCKFROST_PROJECT_ID) {
        return;
      }

      const utxos = await blockfrost.getUTXOs(testAddress);

      expect(Array.isArray(utxos)).toBe(true);
      
      if (utxos.length > 0) {
        const utxo = utxos[0];
        expect(utxo).toHaveProperty('txHash');
        expect(utxo).toHaveProperty('index');
        expect(utxo).toHaveProperty('amount');
        expect(typeof utxo.txHash).toBe('string');
        expect(typeof utxo.index).toBe('number');
        expect(typeof utxo.amount).toBe('string');
      }
    }, 15000);
  });

  describe('Transaction History', () => {
    test('should fetch transaction history', async () => {
      if (!BLOCKFROST_PROJECT_ID) {
        return;
      }

      const transactions = await blockfrost.getTransactionHistory(testAddress, 10);

      expect(Array.isArray(transactions)).toBe(true);
      
      if (transactions.length > 0) {
        const tx = transactions[0];
        expect(tx).toHaveProperty('hash');
        expect(tx).toHaveProperty('chain');
        expect(tx).toHaveProperty('timestamp');
        expect(tx.chain).toBe('cardano');
      }
    }, 30000);
  });

  describe('ADA Handle Resolution', () => {
    test('should resolve a valid ADA handle', async () => {
      if (!BLOCKFROST_PROJECT_ID || TEST_NETWORK !== 'mainnet') {
        return; // Handles are primarily on mainnet
      }

      const address = await blockfrost.resolveAdaHandle(TEST_ADA_HANDLE);

      if (address) {
        expect(typeof address).toBe('string');
        expect(address.startsWith('addr1')).toBe(true);
      }
    }, 15000);

    test('should return null for non-existent handle', async () => {
      if (!BLOCKFROST_PROJECT_ID) {
        return;
      }

      const address = await blockfrost.resolveAdaHandle('$nonexistent_handle_12345xyz');
      expect(address).toBeNull();
    }, 15000);

    test('should handle handle with and without $ prefix', async () => {
      if (!BLOCKFROST_PROJECT_ID || TEST_NETWORK !== 'mainnet') {
        return;
      }

      const handleWithPrefix = await blockfrost.resolveAdaHandle('$adahandle');
      const handleWithoutPrefix = await blockfrost.resolveAdaHandle('adahandle');

      // Both should resolve to the same address
      expect(handleWithPrefix).toBe(handleWithoutPrefix);
    }, 15000);
  });

  describe('Latest Block Info', () => {
    test('should fetch latest block information', async () => {
      if (!BLOCKFROST_PROJECT_ID) {
        return;
      }

      const blockInfo = await blockfrost.getLatestBlock();

      expect(blockInfo).toHaveProperty('slot');
      expect(blockInfo).toHaveProperty('height');
      expect(blockInfo).toHaveProperty('hash');
      expect(typeof blockInfo.slot).toBe('number');
      expect(typeof blockInfo.height).toBe('number');
      expect(blockInfo.slot).toBeGreaterThan(0);
      expect(blockInfo.height).toBeGreaterThan(0);
    }, 15000);
  });

  describe('Protocol Parameters', () => {
    test('should fetch protocol parameters', async () => {
      if (!BLOCKFROST_PROJECT_ID) {
        return;
      }

      const params = await blockfrost.getProtocolParameters();

      expect(params).toBeDefined();
      expect(params).toHaveProperty('min_fee_a');
      expect(params).toHaveProperty('min_fee_b');
      expect(params).toHaveProperty('max_tx_size');
    }, 15000);
  });

  describe('Fee Estimation', () => {
    test('should estimate transaction fees', async () => {
      if (!BLOCKFROST_PROJECT_ID) {
        return;
      }

      const fees = await blockfrost.estimateFees();

      expect(fees).toHaveProperty('slow');
      expect(fees).toHaveProperty('medium');
      expect(fees).toHaveProperty('fast');
      expect(BigInt(fees.slow)).toBeLessThanOrEqual(BigInt(fees.medium));
      expect(BigInt(fees.medium)).toBeLessThanOrEqual(BigInt(fees.fast));
    });
  });

  describe('Asset Metadata', () => {
    test('should fetch metadata for a known asset', async () => {
      if (!BLOCKFROST_PROJECT_ID || TEST_NETWORK !== 'mainnet') {
        return;
      }

      // HOSKY token policy ID + asset name (mainnet example)
      const hoskyPolicyId = 'a0028f350aaabe0545fdcb56b039bfb08e4bb4d8c4d7c3c7d481c235';
      const hoskyAssetName = '484f534b59'; // "HOSKY" in hex
      const assetId = `${hoskyPolicyId}${hoskyAssetName}`;

      const metadata = await blockfrost.getAssetMetadata(assetId);

      if (metadata) {
        expect(metadata).toHaveProperty('policyId');
        expect(metadata).toHaveProperty('assetName');
        expect(metadata.policyId).toBe(hoskyPolicyId);
      }
    }, 15000);
  });

  describe('Caching Mechanism', () => {
    test('should cache repeated requests', async () => {
      if (!BLOCKFROST_PROJECT_ID) {
        return;
      }

      const start1 = Date.now();
      const balance1 = await blockfrost.getBalance(testAddress);
      const time1 = Date.now() - start1;

      const start2 = Date.now();
      const balance2 = await blockfrost.getBalance(testAddress);
      const time2 = Date.now() - start2;

      expect(balance1).toEqual(balance2);
      // Second request should be much faster (cached)
      expect(time2).toBeLessThan(time1 / 2);
    }, 15000);

    test('should allow cache clearing', async () => {
      if (!BLOCKFROST_PROJECT_ID) {
        return;
      }

      await blockfrost.getBalance(testAddress);
      blockfrost.clearCache();
      
      // After clearing cache, this should make a real request
      const balance = await blockfrost.getBalance(testAddress);
      expect(balance).toBeDefined();
    }, 15000);
  });

  describe('Error Handling', () => {
    test('should handle rate limiting gracefully', async () => {
      if (!BLOCKFROST_PROJECT_ID) {
        return;
      }

      // Make multiple rapid requests to potentially trigger rate limiting
      const promises = Array(5).fill(null).map(() => 
        blockfrost.getBalance(testAddress)
      );

      // Should handle rate limits with retries
      await expect(Promise.all(promises)).resolves.toBeDefined();
    }, 30000);

    test('should handle network errors', async () => {
      const badBlockfrost = new BlockfrostAPI({
        projectId: 'invalid_key_12345',
        network: 'testnet',
        maxRetries: 1,
      });

      await expect(
        badBlockfrost.getBalance(testAddress)
      ).rejects.toThrow();
    }, 15000);
  });
});

describe('CardanoWallet with Blockfrost Integration', () => {
  let wallet: CardanoWallet;

  beforeAll(() => {
    if (!BLOCKFROST_PROJECT_ID) {
      return;
    }

    wallet = new CardanoWallet(TEST_NETWORK, {
      projectId: BLOCKFROST_PROJECT_ID,
      network: TEST_NETWORK,
    });
  });

  test('should check Blockfrost availability', () => {
    if (!BLOCKFROST_PROJECT_ID) {
      return;
    }

    expect(wallet.isBlockfrostAvailable()).toBe(true);
  });

  test('should fetch balance through wallet', async () => {
    if (!BLOCKFROST_PROJECT_ID) {
      return;
    }

    const testAddress = TEST_ADDRESSES[TEST_NETWORK];
    const balance = await wallet.getBalance(testAddress);

    expect(balance).toBeDefined();
    expect(balance.chain).toBe('cardano');
  }, 15000);

  test('should fetch UTXOs through wallet', async () => {
    if (!BLOCKFROST_PROJECT_ID) {
      return;
    }

    const testAddress = TEST_ADDRESSES[TEST_NETWORK];
    const utxos = await wallet.getUTXOs(testAddress);

    expect(Array.isArray(utxos)).toBe(true);
  }, 15000);

  test('should resolve ADA handles through wallet', async () => {
    if (!BLOCKFROST_PROJECT_ID || TEST_NETWORK !== 'mainnet') {
      return;
    }

    const address = await wallet.resolveAdaHandle('$adahandle');
    
    if (address) {
      expect(typeof address).toBe('string');
    }
  }, 15000);
});

describe('Production Safety Checks', () => {
  test('should never log API keys', () => {
    const consoleSpy = jest.spyOn(console, 'log');
    const consoleErrorSpy = jest.spyOn(console, 'error');

    const blockfrost = new BlockfrostAPI({
      projectId: 'test_secret_key_12345',
      network: 'testnet',
    });

    expect(consoleSpy).not.toHaveBeenCalledWith(
      expect.stringContaining('test_secret_key_12345')
    );
    expect(consoleErrorSpy).not.toHaveBeenCalledWith(
      expect.stringContaining('test_secret_key_12345')
    );

    consoleSpy.mockRestore();
    consoleErrorSpy.mockRestore();
  });

  test('should redact API keys in error messages', async () => {
    const blockfrost = new BlockfrostAPI({
      projectId: 'secret_key_xyz',
      network: 'testnet',
    });

    try {
      await blockfrost.getBalance('invalid_address');
    } catch (error: any) {
      expect(error.message).not.toContain('secret_key_xyz');
      expect(error.message).toContain('[REDACTED]');
    }
  });
});
