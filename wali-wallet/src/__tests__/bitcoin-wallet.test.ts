/**
 * Bitcoin wallet tests
 */

import { BitcoinWallet } from '../bitcoin/wallet';
import { generateMnemonic } from 'bip39';

describe('BitcoinWallet', () => {
  let wallet: BitcoinWallet;
  let testMnemonic: string;

  beforeEach(() => {
    wallet = new BitcoinWallet('testnet');
    testMnemonic = generateMnemonic(256);
  });

  describe('Address Generation', () => {
    test('should generate valid native-segwit testnet address', async () => {
      const result = await wallet.generateAddress(testMnemonic, 'native-segwit');

      expect(result.address).toMatch(/^tb1/);
      expect(result.publicKey).toBeDefined();
      expect(result.derivationPath).toContain("m/84'/0'/0'/0/0");
    });

    test('should generate legacy address', async () => {
      const result = await wallet.generateAddress(testMnemonic, 'legacy');

      expect(result.address).toMatch(/^[mn]/);
      expect(result.derivationPath).toContain("m/44'/0'/0'/0/0");
    });

    test('should generate segwit address', async () => {
      const result = await wallet.generateAddress(testMnemonic, 'segwit');

      expect(result.address).toMatch(/^2/);
      expect(result.derivationPath).toContain("m/49'/0'/0'/0/0");
    });

    test('should generate consistent addresses from same mnemonic', async () => {
      const result1 = await wallet.generateAddress(testMnemonic, 'native-segwit', 0, 0);
      const result2 = await wallet.generateAddress(testMnemonic, 'native-segwit', 0, 0);

      expect(result1.address).toBe(result2.address);
      expect(result1.publicKey).toBe(result2.publicKey);
    });

    test('should generate different addresses for different indices', async () => {
      const result1 = await wallet.generateAddress(testMnemonic, 'native-segwit', 0, 0);
      const result2 = await wallet.generateAddress(testMnemonic, 'native-segwit', 0, 1);

      expect(result1.address).not.toBe(result2.address);
    });

    test('should generate different addresses for different accounts', async () => {
      const result1 = await wallet.generateAddress(testMnemonic, 'native-segwit', 0, 0);
      const result2 = await wallet.generateAddress(testMnemonic, 'native-segwit', 1, 0);

      expect(result1.address).not.toBe(result2.address);
    });

    test('should handle mainnet addresses', async () => {
      const mainnetWallet = new BitcoinWallet('mainnet');
      const result = await mainnetWallet.generateAddress(testMnemonic, 'native-segwit');

      expect(result.address).toMatch(/^bc1/);
    });
  });

  describe('Transaction Building', () => {
    test('should build PSBT with proper structure', async () => {
      const fromAddr = 'tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx';
      const toAddr = 'tb1q9l0rk0gkgn73d0gc57smxyqrwa9ltpxggrjt3z';
      
      const utxos = [{
        txHash: '0'.repeat(64),
        index: 0,
        amount: 100000
      }];

      const result = await wallet.buildTransaction(
        fromAddr,
        toAddr,
        50000,
        utxos,
        fromAddr,
        10
      );

      expect(result.psbt).toBeDefined();
      expect(result.fee).toBeGreaterThan(0);
      expect(result.preview.from).toBe(fromAddr);
      expect(result.preview.to).toBe(toAddr);
      expect(result.preview.amount).toBe('50000');
    });

    test('should calculate fees based on fee rate', async () => {
      const fromAddr = 'tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx';
      const toAddr = 'tb1q9l0rk0gkgn73d0gc57smxyqrwa9ltpxggrjt3z';
      
      const utxos = [{
        txHash: '0'.repeat(64),
        index: 0,
        amount: 1000000
      }];

      const result1 = await wallet.buildTransaction(
        fromAddr,
        toAddr,
        500000,
        utxos,
        fromAddr,
        1 // 1 sat/byte
      );

      const result2 = await wallet.buildTransaction(
        fromAddr,
        toAddr,
        500000,
        utxos,
        fromAddr,
        10 // 10 sat/byte
      );

      expect(result2.fee).toBeGreaterThan(result1.fee);
    });

    test('should handle dust threshold for change', async () => {
      const fromAddr = 'tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx';
      const toAddr = 'tb1q9l0rk0gkgn73d0gc57smxyqrwa9ltpxggrjt3z';
      
      const utxos = [{
        txHash: '0'.repeat(64),
        index: 0,
        amount: 10000 // Small amount
      }];

      const result = await wallet.buildTransaction(
        fromAddr,
        toAddr,
        9000,
        utxos,
        fromAddr,
        1
      );

      expect(result.psbt).toBeDefined();
      // Change should be absorbed into fee if below dust threshold
    });
  });

  describe('Transaction Signing', () => {
    test('should sign PSBT and return hex', async () => {
      const fromAddr = 'tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx';
      const toAddr = 'tb1q9l0rk0gkgn73d0gc57smxyqrwa9ltpxggrjt3z';
      
      const utxos = [{
        txHash: '0'.repeat(64),
        index: 0,
        amount: 100000
      }];

      const buildResult = await wallet.buildTransaction(
        fromAddr,
        toAddr,
        50000,
        utxos,
        fromAddr,
        10
      );

      const signedTx = await wallet.signTransaction(
        buildResult.psbt,
        testMnemonic,
        'native-segwit',
        0,
        0
      );

      expect(signedTx).toBeDefined();
      expect(typeof signedTx).toBe('string');
      expect(signedTx.length).toBeGreaterThan(0);
    });
  });
});
