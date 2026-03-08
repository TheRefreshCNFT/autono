/**
 * Unit tests for WalletEngine
 */

import { WalletEngine } from '../wallet-engine';
import { generateMnemonic } from 'bip39';

describe('WalletEngine', () => {
  let engine: WalletEngine;

  beforeEach(() => {
    engine = new WalletEngine({
      network: 'testnet'
    });
  });

  describe('Wallet Creation', () => {
    test('should create a new wallet with 24-word mnemonic', async () => {
      const result = await engine.createWallet(['cardano', 'bitcoin'], 24);

      expect(result.mnemonic).toBeDefined();
      expect(result.mnemonic.split(' ')).toHaveLength(24);
      expect(result.addresses.cardano).toBeDefined();
      expect(result.addresses.bitcoin).toBeDefined();
    });

    test('should create wallet with 12-word mnemonic', async () => {
      const result = await engine.createWallet(['cardano', 'bitcoin'], 12);

      expect(result.mnemonic.split(' ')).toHaveLength(12);
    });

    test('should create Cardano-only wallet', async () => {
      const result = await engine.createWallet(['cardano'], 24);

      expect(result.addresses.cardano).toBeDefined();
      expect(result.addresses.bitcoin).toBeUndefined();
    });

    test('should create Bitcoin-only wallet', async () => {
      const result = await engine.createWallet(['bitcoin'], 24);

      expect(result.addresses.bitcoin).toBeDefined();
      expect(result.addresses.cardano).toBeUndefined();
    });

    test('Cardano addresses should start with addr_test1 for testnet', async () => {
      const result = await engine.createWallet(['cardano'], 24);

      expect(result.addresses.cardano).toMatch(/^addr_test1/);
    });

    test('Bitcoin addresses should start with tb1 or m/n for testnet', async () => {
      const result = await engine.createWallet(['bitcoin'], 24);

      expect(result.addresses.bitcoin).toMatch(/^(tb1|m|n)/);
    });
  });

  describe('Wallet Import', () => {
    test('should import wallet from valid mnemonic', async () => {
      const mnemonic = generateMnemonic(256);
      
      const addresses = await engine.importWallet({
        mnemonic,
        chains: ['cardano', 'bitcoin'],
        network: 'testnet'
      });

      expect(addresses.cardano).toBeDefined();
      expect(addresses.bitcoin).toBeDefined();
    });

    test('should generate same address from same mnemonic', async () => {
      const mnemonic = generateMnemonic(256);

      const addresses1 = await engine.importWallet({
        mnemonic,
        chains: ['cardano', 'bitcoin']
      });

      const addresses2 = await engine.importWallet({
        mnemonic,
        chains: ['cardano', 'bitcoin']
      });

      expect(addresses1.cardano).toBe(addresses2.cardano);
      expect(addresses1.bitcoin).toBe(addresses2.bitcoin);
    });

    test('should throw error for invalid mnemonic', async () => {
      await expect(
        engine.importWallet({
          mnemonic: 'invalid mnemonic phrase',
          chains: ['cardano']
        })
      ).rejects.toThrow();
    });
  });

  describe('Address Validation', () => {
    test('should validate correct Cardano mainnet address', () => {
      const validAddress = 'addr1qxyz123456789abcdefghijklmnopqrstuvwxyz123456789abcdefghijklm';
      expect(engine.validateAddress(validAddress, 'cardano')).toBe(true);
    });

    test('should validate correct Cardano testnet address', () => {
      const validAddress = 'addr_test1qxyz123456789abcdefghijklmnopqrstuvwxyz123456789abc';
      expect(engine.validateAddress(validAddress, 'cardano')).toBe(true);
    });

    test('should reject invalid Cardano address', () => {
      expect(engine.validateAddress('invalid_address', 'cardano')).toBe(false);
    });

    test('should validate correct Bitcoin address', () => {
      const validAddresses = [
        '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa', // P2PKH
        '3J98t1WpEZ73CNmYviecrnyiWrnqRhWNLy', // P2SH
        'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4' // Bech32
      ];

      validAddresses.forEach(addr => {
        expect(engine.validateAddress(addr, 'bitcoin')).toBe(true);
      });
    });

    test('should reject invalid Bitcoin address', () => {
      expect(engine.validateAddress('invalid_btc_address', 'bitcoin')).toBe(false);
    });
  });

  describe('Security', () => {
    test('should not leak mnemonic in error messages', async () => {
      try {
        await engine.importWallet({
          mnemonic: 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about',
          chains: ['cardano']
        });
      } catch (error: any) {
        expect(error.message).not.toContain('abandon');
      }
    });

    test('should sanitize addresses in error messages', async () => {
      const testAddress = 'addr_test1qxyz123456789abcdefghijklmnopqrstuvwxyz123456789abc';
      
      try {
        // Force an error with an address
        await engine.buildTransaction({
          chain: 'cardano',
          from: testAddress,
          to: 'invalid',
          amount: '1000000'
        }, 'invalid mnemonic');
      } catch (error: any) {
        expect(error.message).not.toContain(testAddress);
      }
    });
  });
});
