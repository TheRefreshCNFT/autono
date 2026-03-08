/**
 * Cardano wallet tests
 */

import { CardanoWallet } from '../cardano/wallet';
import { generateMnemonic } from 'bip39';

describe('CardanoWallet', () => {
  let wallet: CardanoWallet;
  let testMnemonic: string;

  beforeEach(() => {
    wallet = new CardanoWallet('testnet');
    testMnemonic = generateMnemonic(256);
  });

  describe('Address Generation', () => {
    test('should generate valid testnet address', async () => {
      const result = await wallet.generateAddress(testMnemonic);

      expect(result.address).toMatch(/^addr_test1/);
      expect(result.paymentKey).toBeDefined();
      expect(result.stakeKey).toBeDefined();
    });

    test('should generate consistent addresses from same mnemonic', async () => {
      const result1 = await wallet.generateAddress(testMnemonic, 0, 0);
      const result2 = await wallet.generateAddress(testMnemonic, 0, 0);

      expect(result1.address).toBe(result2.address);
      expect(result1.paymentKey).toBe(result2.paymentKey);
      expect(result1.stakeKey).toBe(result2.stakeKey);
    });

    test('should generate different addresses for different indices', async () => {
      const result1 = await wallet.generateAddress(testMnemonic, 0, 0);
      const result2 = await wallet.generateAddress(testMnemonic, 0, 1);

      expect(result1.address).not.toBe(result2.address);
    });

    test('should generate different addresses for different accounts', async () => {
      const result1 = await wallet.generateAddress(testMnemonic, 0, 0);
      const result2 = await wallet.generateAddress(testMnemonic, 1, 0);

      expect(result1.address).not.toBe(result2.address);
    });

    test('should handle mainnet addresses', async () => {
      const mainnetWallet = new CardanoWallet('mainnet');
      const result = await mainnetWallet.generateAddress(testMnemonic);

      expect(result.address).toMatch(/^addr1/);
    });
  });

  describe('Transaction Building', () => {
    test('should build transaction with proper structure', async () => {
      const fromAddr = 'addr_test1qz2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3jcu5d8ps7zex2k2xt3uqxgjqnnj83ws8lhrn648jjxtwqfjkjv7';
      const toAddr = 'addr_test1qpw0djgj0x59ngrjvqthn7enhvruxnsavsw5th63la3mjel3tkc974sr23jmlzgq5zda4gtv8k9cy38756r9y3qgmkqqjz6aa7';
      
      const utxos = [{
        txHash: '0'.repeat(64),
        index: 0,
        amount: '5000000'
      }];

      const result = await wallet.buildTransaction(
        fromAddr,
        toAddr,
        '1000000',
        utxos,
        fromAddr,
        1000
      );

      expect(result.txBody).toBeDefined();
      expect(result.fee).toBeDefined();
      expect(result.preview.from).toBe(fromAddr);
      expect(result.preview.to).toBe(toAddr);
      expect(result.preview.amount).toBe('1000000');
    });

    test('should calculate fees correctly', async () => {
      const fromAddr = 'addr_test1qz2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3jcu5d8ps7zex2k2xt3uqxgjqnnj83ws8lhrn648jjxtwqfjkjv7';
      const toAddr = 'addr_test1qpw0djgj0x59ngrjvqthn7enhvruxnsavsw5th63la3mjel3tkc974sr23jmlzgq5zda4gtv8k9cy38756r9y3qgmkqqjz6aa7';
      
      const utxos = [{
        txHash: '0'.repeat(64),
        index: 0,
        amount: '10000000'
      }];

      const result = await wallet.buildTransaction(
        fromAddr,
        toAddr,
        '1000000',
        utxos,
        fromAddr
      );

      const fee = BigInt(result.fee);
      expect(fee).toBeGreaterThan(0n);
      expect(fee).toBeLessThan(1000000n); // Should be less than 1 ADA
    });
  });

  describe('Transaction Signing', () => {
    test('should sign transaction and return hex', async () => {
      // Mock transaction body (simplified)
      const txBodyHex = 'a400818258200000000000000000000000000000000000000000000000000000000000000000000182825839000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001a000f4240021a0002a3a9031a0000000a';

      const signedTx = await wallet.signTransaction(
        txBodyHex,
        testMnemonic,
        0,
        0
      );

      expect(signedTx).toBeDefined();
      expect(typeof signedTx).toBe('string');
      expect(signedTx.length).toBeGreaterThan(0);
    });
  });
});
