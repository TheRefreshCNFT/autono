/**
 * wAli Engine - The Friendly Crypto Wallet 🦭
 * Your crypto companion that makes wallet operations simple and secure
 * 
 * Integrates:
 * - Wallet Engine (Cardano/Bitcoin operations)
 * - Night Chain (Secure encrypted storage)
 * - Natural language UI (Conversational UX)
 */

import { WalletEngine, WalletEngineConfig } from './wallet-engine';
import { 
  NightChainSecureStorage, 
  createNightChainStorage 
} from './night-chain/integration';
import { 
  SeedPhraseBundle,
  NightTransactionResult 
} from './night-chain/types';
import { wipeMemory, sanitizeError } from './utils/security';
import { MonetizationConfig } from './monetization/types';
import { DAppRegistry } from './monetization/dapp-registry';
import { AdsManager } from './monetization/ads-manager';
import { PaymentProcessor } from './monetization/payment-processor';

export interface WaliConfig {
  network?: 'mainnet' | 'testnet' | 'devnet';
  cardanoAPIKey?: string;
  bitcoinAPIKey?: string;
  blockfrost?: {
    projectId: string;
    network: 'mainnet' | 'testnet';
  };
  
  // Monetization configuration (optional)
  monetization?: MonetizationConfig;
}

export interface WaliWalletCreationResult {
  addresses: {
    cardano?: string;
    bitcoin?: string;
  };
  nightChainAddress: string;
  assetId: string;
  txHash: string;
  recoveryInstructions: string;
}

export interface WaliMessage {
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  details?: string;
  emoji?: string;
}

/**
 * wAli Engine - Your friendly crypto companion 🦭
 * 
 * Features:
 * - Conversational UX (talk to your wallet like a friend)
 * - Multi-chain support (Cardano, Bitcoin, Night)
 * - Secure storage (encrypted on Night blockchain)
 * - Recovery dialog (friendly 4-line challenge)
 * - Access control (3-strike protection)
 */
export class WaliEngine {
  private walletEngine: WalletEngine;
  private nightStorage: NightChainSecureStorage | null = null;
  private network: 'mainnet' | 'testnet' | 'devnet';
  private initialized: boolean = false;
  
  // Monetization infrastructure (optional)
  private dappRegistry?: DAppRegistry;
  private adsManager?: AdsManager;
  private paymentProcessor?: PaymentProcessor;
  private monetizationConfig?: MonetizationConfig;

  constructor(config: WaliConfig = {}) {
    this.network = config.network || 'testnet';
    this.monetizationConfig = config.monetization;
    
    // Initialize wallet engine with Night chain encryption hooks and Blockfrost
    this.walletEngine = new WalletEngine({
      network: this.network === 'devnet' ? 'testnet' : this.network,
      blockfrost: config.blockfrost,
      encryptBeforeStorage: async (data: Uint8Array) => {
        // This will be connected to Night chain encryption
        return data;
      },
      decryptAfterRetrieval: async (data: Uint8Array) => {
        // This will be connected to Night chain decryption
        return data;
      }
    });
    
    // Initialize monetization if enabled
    if (this.monetizationConfig) {
      this.initializeMonetization();
    }
  }
  
  /**
   * Initialize monetization infrastructure
   */
  private initializeMonetization(): void {
    if (!this.monetizationConfig) return;
    
    // Initialize dApp Registry
    if (this.monetizationConfig.dappIntegrations?.enabled) {
      this.dappRegistry = new DAppRegistry();
    }
    
    // Initialize Ads Manager
    if (this.monetizationConfig.advertisements?.enabled) {
      this.adsManager = new AdsManager({
        respectDoNotTrack: this.monetizationConfig.advertisements.respectDoNotTrack,
        requireUserConsent: this.monetizationConfig.advertisements.requireUserConsent,
        maxAdsPerSession: this.monetizationConfig.advertisements.maxPerSession,
        maxAdsPerDay: this.monetizationConfig.advertisements.maxPerDay,
      });
    }
    
    // Initialize Payment Processor
    if (this.monetizationConfig.payments) {
      this.paymentProcessor = new PaymentProcessor({
        cardanoEnabled: this.monetizationConfig.payments.acceptCardano,
        cardanoPaymentAddress: this.monetizationConfig.payments.cardanoPaymentAddress,
        cardanoNetwork: this.network === 'mainnet' ? 'mainnet' : 'testnet',
        webhookUrl: this.monetizationConfig.payments.webhookUrl,
        webhookSecret: this.monetizationConfig.payments.webhookSecret,
      });
    }
  }
  
  /**
   * Get dApp Registry (if enabled)
   */
  getDAppRegistry(): DAppRegistry | undefined {
    return this.dappRegistry;
  }
  
  /**
   * Get Ads Manager (if enabled)
   */
  getAdsManager(): AdsManager | undefined {
    return this.adsManager;
  }
  
  /**
   * Get Payment Processor (if enabled)
   */
  getPaymentProcessor(): PaymentProcessor | undefined {
    return this.paymentProcessor;
  }

  /**
   * Initialize wAli - Get the walrus ready! 🦭
   */
  async initialize(): Promise<WaliMessage> {
    try {
      // Initialize Night chain storage
      this.nightStorage = await createNightChainStorage(this.network);
      
      this.initialized = true;
      
      return {
        type: 'success',
        message: 'wAli is ready to help! 🦭',
        details: `Connected to ${this.network} network`,
        emoji: '✨'
      };
    } catch (error: any) {
      return {
        type: 'error',
        message: 'Oops! wAli had trouble waking up.',
        details: sanitizeError(error).message,
        emoji: '😴'
      };
    }
  }

  /**
   * Create a new wAli wallet - The complete flow! 🎉
   * 
   * Flow:
   * 1. Generate mnemonics for Cardano & Bitcoin
   * 2. Create addresses
   * 3. Encrypt with user's access key
   * 4. Store on Night blockchain
   * 5. Verify accessibility
   * 6. Wipe plaintext
   * 7. Return success + recovery info
   */
  async createWallet(
    accessKey: string,
    chains: ('cardano' | 'bitcoin')[] = ['cardano', 'bitcoin']
  ): Promise<WaliWalletCreationResult> {
    if (!this.initialized || !this.nightStorage) {
      throw new Error('wAli not initialized. Call initialize() first!');
    }

    try {
      console.log('🦭 wAli: Creating your wallet...');
      
      // Step 1: Generate wallet with mnemonics
      const walletResult = await this.walletEngine.createWallet(chains, 24);
      
      console.log('🦭 wAli: Generated addresses for your coins!');
      
      // Step 2: Prepare seed phrase bundle
      const encoder = new TextEncoder();
      const bundle: SeedPhraseBundle = {
        version: '1.0',
        timestamp: Date.now(),
        cardanoMnemonic: walletResult.addresses.cardano 
          ? new TextDecoder().decode(walletResult.mnemonic)
          : undefined,
        bitcoinMnemonic: walletResult.addresses.bitcoin
          ? new TextDecoder().decode(walletResult.mnemonic)
          : undefined
      };
      
      // Step 3: Encrypt and store on Night chain
      console.log('🦭 wAli: Securing your wallet on Night blockchain...');
      
      const txResult = await this.nightStorage.storeSeedPhrases(bundle, accessKey);
      
      console.log('🦭 wAli: Your wallet is secure! ✨');
      
      // Step 4: Wipe the original mnemonic (already done in nightStorage)
      wipeMemory(walletResult.mnemonic);
      
      // Step 5: Generate recovery instructions
      const recoveryInstructions = this.generateRecoveryInstructions(
        txResult.assetId,
        accessKey.length
      );
      
      return {
        addresses: walletResult.addresses,
        nightChainAddress: this.nightStorage.getWalletAddress() || '',
        assetId: txResult.assetId,
        txHash: txResult.txHash,
        recoveryInstructions
      };
      
    } catch (error: any) {
      throw sanitizeError(error);
    }
  }

  /**
   * Start wallet recovery - Friendly dialog approach 🔑
   */
  async startRecovery(assetId: string): Promise<{
    challengeId: string;
    message: WaliMessage;
  }> {
    if (!this.initialized || !this.nightStorage) {
      throw new Error('wAli not initialized');
    }

    try {
      const challengeId = await this.nightStorage.startRecovery(assetId);
      
      return {
        challengeId,
        message: {
          type: 'info',
          message: 'Let\'s recover your wallet! 🦭',
          details: 'I\'ll ask you a few friendly questions to verify it\'s you.',
          emoji: '🔍'
        }
      };
    } catch (error: any) {
      throw sanitizeError(error);
    }
  }

  /**
   * Submit recovery input with friendly feedback
   */
  submitRecoveryInput(challengeId: string, input: string): WaliMessage {
    if (!this.nightStorage) {
      throw new Error('wAli not initialized');
    }

    const state = this.nightStorage.submitRecoveryInput(challengeId, input);
    
    // Convert to friendly message
    if (state.step === 'complete') {
      return {
        type: 'success',
        message: 'Great! Now enter your access key to unlock your wallet. 🔓',
        emoji: '✅'
      };
    } else {
      return {
        type: 'info',
        message: state.currentPrompt || 'Waiting for recovery input...',
        details: `Step ${state.step === 'user-line-1' ? '1' : state.step === 'bot-line-1' ? '2' : state.step === 'user-line-2' ? '3' : '4'} of 4`,
        emoji: '💭'
      };
    }
  }

  /**
   * Complete recovery and get seed phrases
   */
  async completeRecovery(
    challengeId: string,
    accessKey: string
  ): Promise<{
    addresses: { cardano?: string; bitcoin?: string };
    message: WaliMessage;
  }> {
    if (!this.nightStorage) {
      throw new Error('wAli not initialized');
    }

    try {
      // Recover the seed bundle
      const bundle = await this.nightStorage.completeRecovery(challengeId, accessKey);
      
      // Import wallet from recovered mnemonics
      const encoder = new TextEncoder();
      const chains: ('cardano' | 'bitcoin')[] = [];
      
      if (bundle.cardanoMnemonic) chains.push('cardano');
      if (bundle.bitcoinMnemonic) chains.push('bitcoin');
      
      // Use the first available mnemonic (they're the same)
      const mnemonicStr = bundle.cardanoMnemonic || bundle.bitcoinMnemonic || '';
      const mnemonic = encoder.encode(mnemonicStr);
      
      const addresses = await this.walletEngine.importWallet({
        mnemonic,
        chains
      });
      
      // Wipe recovered plaintext
      wipeMemory(mnemonic);
      
      return {
        addresses,
        message: {
          type: 'success',
          message: 'Welcome back! Your wallet is restored. 🎉',
          details: 'wAli missed you!',
          emoji: '🦭'
        }
      };
      
    } catch (error: any) {
      return {
        addresses: {},
        message: {
          type: 'error',
          message: 'Hmm, that didn\'t work.',
          details: error.message,
          emoji: '🤔'
        }
      };
    }
  }

  /**
   * Build a transaction with friendly feedback
   */
  async buildTransaction(request: any, mnemonic: Uint8Array): Promise<any> {
    try {
      console.log('🦭 wAli: Building your transaction...');
      
      const unsignedTx = await this.walletEngine.buildTransaction(request, mnemonic);
      
      console.log('🦭 wAli: Transaction ready! Check the preview.');
      
      return unsignedTx;
    } catch (error: any) {
      throw sanitizeError(error);
    }
  }

  /**
   * Sign and broadcast transaction
   */
  async sendTransaction(unsignedTx: any, mnemonic: Uint8Array): Promise<{
    txHash: string;
    message: WaliMessage;
  }> {
    try {
      console.log('🦭 wAli: Signing your transaction...');
      
      const signed = await this.walletEngine.signTransaction(unsignedTx, mnemonic);
      
      console.log('🦭 wAli: Broadcasting to the network...');
      
      const txHash = await this.walletEngine.broadcastTransaction(signed);
      
      return {
        txHash,
        message: {
          type: 'success',
          message: 'Transaction sent! 🚀',
          details: `Hash: ${txHash.substring(0, 16)}...`,
          emoji: '✅'
        }
      };
    } catch (error: any) {
      throw sanitizeError(error);
    }
  }

  /**
   * Get balances with friendly formatting
   */
  async getBalances(addresses: any): Promise<any> {
    try {
      return await this.walletEngine.getBalances(addresses);
    } catch (error: any) {
      throw sanitizeError(error);
    }
  }

  /**
   * Generate friendly recovery instructions
   */
  private generateRecoveryInstructions(assetId: string, accessKeyLength: number): string {
    return `
🦭 wAli Recovery Information 🦭

Your wallet is safely stored on the Night blockchain!

Asset ID: ${assetId}

To recover your wallet:
1. Start recovery with your Asset ID
2. Answer 4 simple questions (recovery dialog)
3. Enter your ${accessKeyLength}-character access key
4. wAli will restore your wallet!

⚠️ IMPORTANT:
- Keep your access key secret
- Write down your Asset ID
- You have 3 attempts before lockout
- wAli can't help if you lose both!

Stay safe out there! 🦭✨
    `.trim();
  }

  /**
   * Disconnect and cleanup
   */
  async disconnect(): Promise<WaliMessage> {
    if (this.nightStorage) {
      await this.nightStorage.disconnect();
    }
    
    this.initialized = false;
    
    return {
      type: 'info',
      message: 'wAli is taking a nap. See you soon! 😴',
      emoji: '👋'
    };
  }
}

export default WaliEngine;
