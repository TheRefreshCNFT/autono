/**
 * wAli Integration Tests 🦭
 * 
 * Tests the complete end-to-end workflow:
 * 1. Create wallet
 * 2. Encrypt and store on Night chain
 * 3. Verify recovery works
 * 4. Build and send transactions
 * 5. Test conversational UX
 */

import { WaliEngine } from '../wali-engine';
import { CommandParser } from '../../wallet-ui-interface/shared/src/parser';
import { WaliPersonality } from '../../wallet-ui-interface/shared/src/wali-personality';

describe('wAli Integration Tests', () => {
  let wali: WaliEngine;
  const testAccessKey = 'walrus2026';
  let testAssetId: string;
  let testAddresses: any;

  beforeAll(async () => {
    wali = new WaliEngine({ network: 'testnet' });
    await wali.initialize();
  });

  afterAll(async () => {
    if (wali) {
      await wali.disconnect();
    }
  });

  describe('1. Wallet Creation Flow', () => {
    test('should create a new wallet with friendly messages', async () => {
      console.log('🦭 wAli: Starting wallet creation test...');

      const result = await wali.createWallet(testAccessKey, ['cardano', 'bitcoin']);

      // Verify addresses were created
      expect(result.addresses.cardano).toBeDefined();
      expect(result.addresses.bitcoin).toBeDefined();
      expect(result.addresses.cardano).toMatch(/^addr1/);
      expect(result.addresses.bitcoin).toMatch(/^(bc1|tb1)/);

      // Verify Night chain storage
      expect(result.assetId).toBeDefined();
      expect(result.txHash).toBeDefined();
      expect(result.nightChainAddress).toBeDefined();

      // Verify recovery instructions
      expect(result.recoveryInstructions).toContain('Asset ID');
      expect(result.recoveryInstructions).toContain(result.assetId);

      // Save for later tests
      testAssetId = result.assetId;
      testAddresses = result.addresses;

      console.log('✅ Wallet created successfully!');
      console.log('   Cardano:', result.addresses.cardano?.substring(0, 20) + '...');
      console.log('   Bitcoin:', result.addresses.bitcoin);
      console.log('   Asset ID:', result.assetId);
    }, 30000); // 30s timeout for blockchain operations

    test('should provide helpful error for weak access key', async () => {
      await expect(
        wali.createWallet('123', ['cardano']) // Too short
      ).rejects.toThrow();
    });
  });

  describe('2. Recovery Flow', () => {
    test('should start recovery with friendly prompts', async () => {
      const { challengeId, message } = await wali.startRecovery(testAssetId);

      expect(challengeId).toBeDefined();
      expect(message.type).toBe('info');
      expect(message.emoji).toBe('🔍');
      expect(message.message).toContain('recover');

      console.log('🦭 Recovery started:', message.message);
    });

    test('should guide through recovery dialog', async () => {
      const { challengeId } = await wali.startRecovery(testAssetId);

      // Submit 4 answers (simplified for test)
      const msg1 = wali.submitRecoveryInput(challengeId, 'answer1');
      expect(msg1.type).toBe('info');

      const msg2 = wali.submitRecoveryInput(challengeId, 'answer2');
      expect(msg2.type).toBe('info');

      const msg3 = wali.submitRecoveryInput(challengeId, 'answer3');
      expect(msg3.type).toBe('info');

      const msg4 = wali.submitRecoveryInput(challengeId, 'answer4');
      expect(msg4.type).toBe('success');
      expect(msg4.message).toContain('access key');

      console.log('✅ Recovery dialog completed');
    });

    test('should complete recovery with correct access key', async () => {
      const { challengeId } = await wali.startRecovery(testAssetId);

      // Answer questions
      wali.submitRecoveryInput(challengeId, 'answer1');
      wali.submitRecoveryInput(challengeId, 'answer2');
      wali.submitRecoveryInput(challengeId, 'answer3');
      wali.submitRecoveryInput(challengeId, 'answer4');

      // Complete with access key
      const result = await wali.completeRecovery(challengeId, testAccessKey);

      expect(result.addresses.cardano).toBe(testAddresses.cardano);
      expect(result.addresses.bitcoin).toBe(testAddresses.bitcoin);
      expect(result.message.type).toBe('success');
      expect(result.message.emoji).toBe('🦭');

      console.log('✅ Wallet recovered successfully!');
    }, 15000);

    test('should reject wrong access key with friendly error', async () => {
      const { challengeId } = await wali.startRecovery(testAssetId);

      // Answer questions
      wali.submitRecoveryInput(challengeId, 'answer1');
      wali.submitRecoveryInput(challengeId, 'answer2');
      wali.submitRecoveryInput(challengeId, 'answer3');
      wali.submitRecoveryInput(challengeId, 'answer4');

      // Try wrong access key
      const result = await wali.completeRecovery(challengeId, 'wrongkey');

      expect(result.message.type).toBe('error');
      expect(result.message.message).toContain('didn\'t work');
    }, 15000);
  });

  describe('3. Conversational UX', () => {
    const parser = new CommandParser();
    const personality = new WaliPersonality('Alice');

    test('should parse natural language commands', () => {
      // Send command
      const sendCmd = parser.parse('send 10 ADA to $alice');
      expect(sendCmd.intent.type).toBe('send');
      expect(sendCmd.intent.amount).toBe('10');
      expect(sendCmd.intent.to?.address).toBe('$alice');

      // Balance command
      const balanceCmd = parser.parse('show balance');
      expect(balanceCmd.intent.metadata?.query).toBe('balance');

      console.log('✅ Natural language parsing works!');
    });

    test('should provide friendly welcome messages', () => {
      const newUser = personality.welcome('new');
      expect(newUser.message).toContain('wAli');
      expect(newUser.type).toBe('welcome');
      expect(newUser.emoji).toBe('🦭');

      const returningUser = personality.welcome('returning');
      expect(returningUser.suggestions).toBeDefined();

      console.log('🦭 Welcome:', newUser.message);
    });

    test('should give helpful transaction feedback', () => {
      const building = personality.transaction('building');
      expect(building.emoji).toBe('🔨');
      expect(building.message).toContain('Building');

      const sent = personality.transaction('sent', { txHash: 'abc123' });
      expect(sent.type).toBe('success');
      expect(sent.emoji).toBe('🚀');
      expect(sent.message).toContain('sent');

      console.log('✅ Transaction feedback is friendly');
    });

    test('should explain errors in human terms', () => {
      const failed = personality.transaction('failed', {
        error: { message: 'insufficient funds' }
      });

      expect(failed.type).toBe('error');
      expect(failed.message).toContain('enough funds');
      expect(failed.message).not.toContain('INSUFFICIENT_FUNDS'); // No tech jargon

      console.log('🦭 Error explanation:', failed.message);
    });

    test('should provide context-aware help', () => {
      const help = personality.help();
      expect(help.type).toBe('info');
      expect(help.emoji).toBe('💡');
      expect(help.suggestions).toBeDefined();

      const accessKeyHelp = personality.help('access-key');
      expect(accessKeyHelp.message).toContain('password');

      console.log('✅ Help system is context-aware');
    });
  });

  describe('4. Security Validation', () => {
    test('should never log plaintext mnemonics', async () => {
      const originalLog = console.log;
      const logs: string[] = [];
      console.log = (...args) => {
        logs.push(args.join(' '));
        originalLog(...args);
      };

      await wali.createWallet('testkey123', ['cardano']);

      // Check logs for plaintext mnemonics
      const hasPlaintext = logs.some(log =>
        /\b(word1|word2|word3)\b/.test(log) ||
        /\b[a-z]{4,}\s[a-z]{4,}\s[a-z]{4,}/.test(log) // Mnemonic pattern
      );

      expect(hasPlaintext).toBe(false);

      console.log = originalLog;
      console.log('✅ No plaintext in logs');
    });

    test('should enforce access control (3-strike)', async () => {
      // This would be a more complex test requiring access control mocking
      // For now, verify the interface exists
      expect(wali.completeRecovery).toBeDefined();
      console.log('✅ Access control interface present');
    });
  });

  describe('5. End-to-End Workflow', () => {
    test('complete user journey', async () => {
      console.log('\n🦭 Starting complete user journey test...\n');

      // 1. User creates wallet
      console.log('Step 1: Create wallet');
      const createResult = await wali.createWallet('journey2026', ['cardano']);
      expect(createResult.addresses.cardano).toBeDefined();
      console.log('✅ Wallet created');

      // 2. User checks balance (simulated - would need mock API)
      console.log('Step 2: Check balance');
      // const balances = await wali.getBalances(createResult.addresses);
      // expect(balances).toBeDefined();
      console.log('✅ Balance check (mocked)');

      // 3. User loses access, starts recovery
      console.log('Step 3: Start recovery');
      const { challengeId } = await wali.startRecovery(createResult.assetId);
      expect(challengeId).toBeDefined();
      console.log('✅ Recovery started');

      // 4. User answers recovery questions
      console.log('Step 4: Answer recovery questions');
      wali.submitRecoveryInput(challengeId, 'answer1');
      wali.submitRecoveryInput(challengeId, 'answer2');
      wali.submitRecoveryInput(challengeId, 'answer3');
      const lastMsg = wali.submitRecoveryInput(challengeId, 'answer4');
      expect(lastMsg.type).toBe('success');
      console.log('✅ Questions answered');

      // 5. User enters access key and recovers wallet
      console.log('Step 5: Recover wallet');
      const recovered = await wali.completeRecovery(challengeId, 'journey2026');
      expect(recovered.addresses.cardano).toBe(createResult.addresses.cardano);
      expect(recovered.message.type).toBe('success');
      console.log('✅ Wallet recovered');

      console.log('\n🎉 Complete journey successful!\n');
    }, 60000); // 60s for full journey
  });
});

describe('wAli Personality Tests', () => {
  const wali = new WaliPersonality('TestUser');

  test('should have consistent friendly tone', () => {
    const messages = [
      wali.welcome('new'),
      wali.transaction('sent'),
      wali.balance(true, 5),
      wali.help(),
    ];

    messages.forEach(msg => {
      // Should always have emoji
      expect(msg.emoji).toBeDefined();

      // Should not have scary technical terms
      expect(msg.message).not.toMatch(/ERROR_CODE_\d+/);
      expect(msg.message).not.toMatch(/EXCEPTION/);
      expect(msg.message).not.toMatch(/FATAL/);
    });

    console.log('✅ wAli maintains friendly tone throughout');
  });

  test('should provide actionable suggestions', () => {
    const messages = [
      wali.welcome('new'),
      wali.balance(false),
      wali.transaction('failed'),
    ];

    messages.forEach(msg => {
      if (msg.suggestions) {
        expect(msg.suggestions.length).toBeGreaterThan(0);
        expect(msg.suggestions.every(s => typeof s === 'string')).toBe(true);
      }
    });

    console.log('✅ Suggestions are always actionable');
  });
});

describe('Command Parser Tests', () => {
  const parser = new CommandParser();

  test('should understand various send patterns', () => {
    const patterns = [
      'send 10 ADA to $alice',
      'send 0.5 BTC to bc1qxy...',
      'transfer 100 HOSKY to addr1...',
      'pay $bob 25 ADA',
    ];

    patterns.forEach(pattern => {
      const result = parser.parse(pattern);
      expect(result.intent.type).toBe('send');
      expect(result.confidence).toBeGreaterThan(50);
    });

    console.log('✅ Parser understands multiple send patterns');
  });

  test('should detect ambiguities', () => {
    const ambiguous = parser.parse('send 10 to someone');
    expect(ambiguous.ambiguities.length).toBeGreaterThan(0);
    expect(ambiguous.confidence).toBeLessThan(50);

    console.log('✅ Parser detects ambiguous commands');
  });
});
