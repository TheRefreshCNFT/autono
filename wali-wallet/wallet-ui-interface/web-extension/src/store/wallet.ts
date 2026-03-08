/**
 * Wallet state management using Zustand
 * NOW WIRED TO REAL WALLET ENGINE
 */

import { create } from 'zustand';
import {
  WalletState,
  LoadingState,
  ErrorState,
  ParsedCommand,
  CommandResponse,
  TransactionPreview,
} from '@wallet-ui/shared';
import { getWalletBridge, WalletAddresses } from '../wallet-bridge';

interface WalletStore {
  walletState: WalletState;
  loading: LoadingState;
  error: ErrorState;
  addresses: WalletAddresses | null;
  nightBackupTxId: string | null;
  pendingMnemonic: string | null; // Temporary storage before Night backup
  recoveryChallenge: string[] | null; // 16-word recovery challenge
  transactionPreview: TransactionPreview | null;
  
  // Actions
  processCommand: (command: ParsedCommand) => Promise<CommandResponse>;
  clearError: () => void;
  setLoading: (loading: boolean, operation?: string) => void;
  createWallet: (wordCount?: 12 | 15 | 18 | 21 | 24) => Promise<CommandResponse>;
  backupToNightChain: (accessKey: string) => Promise<CommandResponse>;
  recoverFromNightChain: (challengeWords: string[], accessKey: string) => Promise<CommandResponse>;
  getBalance: (showAddress?: boolean) => Promise<CommandResponse>;
  getTransactionHistory: () => Promise<CommandResponse>;
  sendTransaction: (to: string, amount: string, accessKey: string, chain?: 'cardano' | 'bitcoin') => Promise<CommandResponse>;
  buildTransactionPreview: (to: string, amount: string, chain?: 'cardano' | 'bitcoin') => Promise<CommandResponse>;
}

// Load persisted state from chrome.storage
const loadPersistedState = async (): Promise<Partial<WalletState>> => {
  try {
    const result = await chrome.storage.local.get(['walletState']);
    return result.walletState || {};
  } catch {
    return {};
  }
};

// Save state to chrome.storage
const saveState = async (state: WalletState) => {
  try {
    await chrome.storage.local.set({ walletState: state });
  } catch (e) {
    console.error('Failed to save wallet state:', e);
  }
};

export const useWalletStore = create<WalletStore>((set, get) => ({
  walletState: {
    isInitialized: false,
    isLocked: true,
    accounts: [],
    assets: [],
    connections: [],
  },
  loading: {
    isLoading: false,
  },
  error: {
    hasError: false,
  },
  addresses: null,
  nightBackupTxId: null,
  pendingMnemonic: null,
  recoveryChallenge: null,
  transactionPreview: null,

  /**
   * Create a new wallet with REAL addresses
   * CRITICAL FIX: Creates ALL 3 wallets (Cardano + Bitcoin + Night) simultaneously
   */
  createWallet: async (wordCount: 12 | 15 | 18 | 21 | 24 = 24): Promise<CommandResponse> => {
    const { setLoading } = get();
    
    try {
      setLoading(true, 'Creating your wallet...');

      const bridge = await getWalletBridge();
      
      // CRITICAL: Create ALL THREE chains at once
      const result = await bridge.createWallet({
        wordCount,
        chains: ['cardano', 'bitcoin', 'night'], // All 3!
      });

      // Verify all addresses were created
      if (!result.addresses.cardano || !result.addresses.bitcoin || !result.addresses.night) {
        throw new Error('Failed to create all wallet addresses');
      }

      // Store addresses and pending mnemonic
      const newState = {
        ...get().walletState,
        isInitialized: true,
      };
      
      set({
        addresses: result.addresses,
        pendingMnemonic: result.mnemonic,
        walletState: newState,
      });
      
      // Persist wallet state to chrome.storage
      await saveState(newState);
      
      // Also save addresses for recovery
      await chrome.storage.local.set({
        walletAddresses: result.addresses,
      });

      // Build response showing ALL THREE addresses
      const btcAddrs = result.addresses.bitcoin!;
      
      return {
        success: true,
        message: '🦭 **Wallet Created Successfully!**\n\n' +
          '✅ **All 3 Chains Ready:**\n\n' +
          '**🔷 Cardano Address:**\n' +
          `\`${result.addresses.cardano}\`\n\n` +
          '**₿ Bitcoin Addresses:**\n' +
          `• **SegWit (Recommended):** \`${btcAddrs.segwit}\`\n` +
          `• **Legacy:** \`${btcAddrs.legacy}\`\n` +
          `• **Taproot:** \`${btcAddrs.taproot}\`\n\n` +
          '**🌙 Midnight Address:**\n' +
          `\`${result.addresses.night}\`\n\n` +
          '⚠️ **NEXT STEP:** Backup to Night Chain\n\n' +
          'Please create a 4-12 character access key to encrypt your seed phrase.',
        data: {
          requiresBackup: true,
          addresses: result.addresses,
          showBackupPrompt: true,
        },
      };
    } catch (error: any) {
      set({
        error: {
          hasError: true,
          message: error.message,
          code: error.code,
        },
      });

      return {
        success: false,
        message: `❌ Failed to create wallet: ${error.message}`,
      };
    } finally {
      setLoading(false);
    }
  },

  /**
   * Backup seed phrase to Night Chain
   * CRITICAL FIX: Returns 16-word recovery challenge for display
   */
  backupToNightChain: async (accessKey: string): Promise<CommandResponse> => {
    const { setLoading, pendingMnemonic } = get();
    
    if (!pendingMnemonic) {
      return {
        success: false,
        message: '❌ No pending mnemonic to backup. Create a wallet first.',
      };
    }

    try {
      setLoading(true, 'Encrypting and storing on Night Chain...');

      const bridge = await getWalletBridge();
      const result = await bridge.backupToNightChain({
        mnemonic: pendingMnemonic,
        accessKey,
      });

      if (!result.success) {
        return {
          success: false,
          message: `❌ Backup failed: ${result.error}`,
        };
      }

      // Generate 16-word recovery challenge from mnemonic
      // Take first 16 words from the 24-word seed
      const mnemonicWords = pendingMnemonic.split(' ');
      const challengeWords = mnemonicWords.slice(0, 16);

      // Clear pending mnemonic and store backup tx ID + recovery challenge
      const newState = {
        ...get().walletState,
        isLocked: false,
      };
      
      set({
        pendingMnemonic: null,
        nightBackupTxId: result.transactionId!,
        recoveryChallenge: challengeWords,
        walletState: newState,
      });
      
      // Persist updated wallet state
      await saveState(newState);
      
      // Save night backup info
      await chrome.storage.local.set({
        nightBackupTxId: result.transactionId,
        recoveryChallenge: challengeWords,
      });

      return {
        success: true,
        message: '✅ **Your seed phrase is safely stored on Night Chain!**\n\n' +
          `Transaction ID: \`${result.transactionId}\`\n\n` +
          '⚠️ **CRITICAL: Save Your Recovery Words**\n\n' +
          'You will now see your 16-word recovery challenge.\n' +
          'These are REQUIRED if you forget your access key!',
        data: {
          showRecoveryChallenge: true,
          recoveryChallenge: challengeWords,
          transactionId: result.transactionId,
        },
      };
    } catch (error: any) {
      set({
        error: {
          hasError: true,
          message: error.message,
          code: error.code,
        },
      });

      return {
        success: false,
        message: `❌ Backup failed: ${error.message}`,
      };
    } finally {
      setLoading(false);
    }
  },

  /**
   * Recover wallet from Night Chain using 4-line challenge
   * CRITICAL FIX: New recovery flow
   */
  recoverFromNightChain: async (challengeWords: string[], accessKey: string): Promise<CommandResponse> => {
    const { setLoading } = get();

    if (challengeWords.length !== 16) {
      return {
        success: false,
        message: '❌ Recovery challenge must be exactly 16 words (4 lines × 4 words)',
      };
    }

    try {
      setLoading(true, 'Recovering wallet from Night Chain...');

      const bridge = await getWalletBridge();
      
      // Note: This is a simplified recovery flow
      // In production, you'd use the challenge words to derive the transaction ID
      // For now, we assume the user has the Night Chain TX ID
      // TODO: Implement challenge-based recovery in wallet-bridge.ts
      
      // For now, return error with instructions
      return {
        success: false,
        message: '🚧 **Recovery flow coming soon!**\n\n' +
          'Night Chain recovery requires:\n' +
          '1. Your 16 recovery words (4-line challenge)\n' +
          '2. Your access key\n' +
          '3. Connection to Night Chain network\n\n' +
          'This feature is being finalized in the backend.',
      };

      // TODO: Implement actual recovery
      // const result = await bridge.recoverFromNightChain(txId, accessKey);
      
    } catch (error: any) {
      set({
        error: {
          hasError: true,
          message: error.message,
          code: error.code,
        },
      });

      return {
        success: false,
        message: `❌ Recovery failed: ${error.message}`,
      };
    } finally {
      setLoading(false);
    }
  },

  /**
   * Get REAL balance from Blockfrost
   */
  getBalance: async (showAddress: boolean = false): Promise<CommandResponse> => {
    const { setLoading, addresses } = get();
    
    if (!addresses) {
      return {
        success: false,
        message: '❌ No wallet found. Create a wallet first.',
      };
    }

    if (showAddress) {
      const btcAddrs = addresses.bitcoin!;
      return {
        success: true,
        message: '🦭 **Your Receiving Addresses**\n\n' +
          '**Cardano:**\n' +
          `\`${addresses.cardano}\`\n\n` +
          '**Bitcoin (Choose one):**\n' +
          `• **SegWit (Recommended):** \`${btcAddrs.segwit}\`\n` +
          `• **Legacy:** \`${btcAddrs.legacy}\`\n` +
          `• **Taproot:** \`${btcAddrs.taproot}\`\n\n` +
          '**Night Chain:**\n' +
          `\`${addresses.night}\`\n\n` +
          'Send funds to any of these addresses. I recommend using SegWit for Bitcoin (lower fees).',
      };
    }

    try {
      setLoading(true, 'Fetching real balances...');

      const bridge = await getWalletBridge();
      const balances = await bridge.getBalances(addresses);

      // Format balance response
      let message = '💰 **Your Balance**\n\n';
      
      balances.forEach((bal: any) => {
        message += `**${bal.chain.charAt(0).toUpperCase() + bal.chain.slice(1)}:**\n`;
        message += `• ${bal.balance} ${bal.asset}\n`;
        if (bal.tokens && bal.tokens.length > 0) {
          bal.tokens.forEach((token: any) => {
            message += `• ${token.balance} ${token.symbol}\n`;
          });
        }
        message += '\n';
      });

      return {
        success: true,
        message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: `❌ Failed to fetch balance: ${error.message}`,
      };
    } finally {
      setLoading(false);
    }
  },

  /**
   * Get REAL transaction history from Blockfrost
   */
  getTransactionHistory: async (): Promise<CommandResponse> => {
    const { setLoading, addresses } = get();
    
    if (!addresses) {
      return {
        success: false,
        message: '❌ No wallet found. Create a wallet first.',
      };
    }

    try {
      setLoading(true, 'Fetching transaction history...');

      const bridge = await getWalletBridge();
      const history = await bridge.getTransactionHistory(addresses, 20);

      if (history.length === 0) {
        return {
          success: true,
          message: '📜 **Transaction History**\n\n' +
            'No transactions yet. Send or receive some crypto to get started!',
        };
      }

      let message = '📜 **Recent Transactions**\n\n';
      
      history.forEach((tx: any, idx: number) => {
        if (idx > 0) message += '\n';
        const date = new Date(tx.timestamp * 1000).toLocaleDateString();
        message += `**${date}**\n`;
        message += `• ${tx.type === 'received' ? 'Received' : 'Sent'} ${tx.amount} ${tx.asset}\n`;
        message += `  TX: \`${tx.hash.substring(0, 16)}...\`\n`;
      });

      return {
        success: true,
        message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: `❌ Failed to fetch history: ${error.message}`,
      };
    } finally {
      setLoading(false);
    }
  },

  processCommand: async (command: ParsedCommand): Promise<CommandResponse> => {
    const { createWallet, getBalance, getTransactionHistory, buildTransactionPreview, sendTransaction } = get();
    
    try {
      // Route commands to real implementations
      if (command.intent.type === 'create_wallet') {
        return await createWallet();
      }

      if (command.intent.type === 'show_balance') {
        const showAddress = command.intent.metadata?.showAddress;
        return await getBalance(showAddress);
      }

      if (command.intent.type === 'show_history') {
        return await getTransactionHistory();
      }

      // Implement send transaction
      if (command.intent.type === 'send') {
        const { to, amount } = command.intent.metadata || {};
        
        if (!to || !amount) {
          return {
            success: false,
            message: '❌ Invalid send command. Use: send <amount> to <address or $handle>',
          };
        }

        // Build transaction preview - requires user confirmation
        return await buildTransactionPreview(to, amount);
      }

      // Handle confirm send (user confirms transaction with access key)
      if (command.intent.type === 'confirm_send' || command.text.toLowerCase().includes('confirm send')) {
        const { transactionPreview } = get();
        
        if (!transactionPreview) {
          return {
            success: false,
            message: '❌ No pending transaction to confirm. Use **send** command first.',
          };
        }

        // Extract access key from command (everything after "confirm send")
        const accessKeyMatch = command.text.match(/confirm\s+send\s+(.+)/i);
        const accessKey = accessKeyMatch ? accessKeyMatch[1].trim() : '';

        if (!accessKey) {
          return {
            success: false,
            message: '❌ Please provide your access key: **confirm send <your-access-key>**',
          };
        }

        return await sendTransaction(
          transactionPreview.to,
          transactionPreview.amount,
          accessKey,
          transactionPreview.chain
        );
      }

      // Handle cancel (cancel pending transaction)
      if (command.text.toLowerCase() === 'cancel') {
        const { transactionPreview } = get();
        
        if (transactionPreview) {
          set({ transactionPreview: null });
          return {
            success: true,
            message: '✅ Transaction cancelled.',
          };
        }

        return {
          success: true,
          message: 'Nothing to cancel.',
        };
      }

      return {
        success: true,
        message: 'Command recognized but not yet implemented.',
      };
    } catch (error: any) {
      set({
        error: {
          hasError: true,
          message: error.message,
          code: error.code,
        },
      });

      return {
        success: false,
        message: error.message || 'Failed to process command',
      };
    }
  },

  clearError: () => {
    set({ error: { hasError: false } });
  },

  setLoading: (isLoading: boolean, operation?: string) => {
    set({ loading: { isLoading, operation } });
  },

  /**
   * Build transaction preview (estimates fees, validates amount)
   */
  buildTransactionPreview: async (
    to: string,
    amount: string,
    chain: 'cardano' | 'bitcoin' = 'cardano'
  ): Promise<CommandResponse> => {
    const { setLoading, addresses, nightBackupTxId } = get();

    if (!addresses) {
      return {
        success: false,
        message: '❌ No wallet found. Create a wallet first.',
      };
    }

    if (!nightBackupTxId) {
      return {
        success: false,
        message: '❌ Wallet not backed up to Night Chain. Cannot send funds without backup.',
      };
    }

    try {
      setLoading(true, 'Building transaction...');

      const bridge = await getWalletBridge();
      
      // Resolve ADA handle if needed
      let recipient = to;
      if (to.startsWith('$')) {
        const resolved = await bridge.resolveAdaHandle(to.substring(1));
        if (!resolved) {
          return {
            success: false,
            message: `❌ Could not resolve handle: ${to}`,
          };
        }
        recipient = resolved;
      }

      // Validate address format
      const fromAddress = chain === 'cardano' ? addresses.cardano : addresses.bitcoin.segwit;
      
      // Parse amount
      const numAmount = parseFloat(amount);
      if (isNaN(numAmount) || numAmount <= 0) {
        return {
          success: false,
          message: '❌ Invalid amount. Must be a positive number.',
        };
      }

      // For now, estimate a fixed fee (in production, would calculate from UTXO set)
      const estimatedFee = chain === 'cardano' ? '0.17' : '0.0001'; // ADA or BTC
      const total = (numAmount + parseFloat(estimatedFee)).toFixed(chain === 'cardano' ? 2 : 8);
      
      // Store transaction preview
      const preview: TransactionPreview = {
        from: fromAddress,
        to: recipient,
        amount,
        fee: estimatedFee,
        total,
        chain,
      };

      set({ transactionPreview: preview });

      const symbol = chain === 'cardano' ? 'ADA' : 'BTC';
      let message = '💳 **Transaction Preview**\n\n';
      message += `**Sending:** ${amount} ${symbol}\n`;
      message += `**To:** ${recipient}\n`;
      if (to !== recipient) {
        message += `**Handle:** ${to}\n`;
      }
      message += `**Fee:** ${estimatedFee} ${symbol}\n`;
      message += `**Total:** ${total} ${symbol}\n\n`;
      message += `⚠️ This transaction will be signed with your Night Chain backup.\n`;
      message += `To continue, use: **confirm send <access-key>**\n`;
      message += `To cancel: **cancel**`;

      return {
        success: true,
        message,
        showTransactionPreview: true,
      };
    } catch (error: any) {
      return {
        success: false,
        message: `❌ Failed to build transaction: ${error.message}`,
      };
    } finally {
      setLoading(false);
    }
  },

  /**
   * Send transaction (confirms and broadcasts)
   */
  sendTransaction: async (
    to: string,
    amount: string,
    accessKey: string,
    chain: 'cardano' | 'bitcoin' = 'cardano'
  ): Promise<CommandResponse> => {
    const { setLoading, addresses, nightBackupTxId, transactionPreview } = get();

    if (!addresses) {
      return {
        success: false,
        message: '❌ No wallet found. Create a wallet first.',
      };
    }

    if (!nightBackupTxId) {
      return {
        success: false,
        message: '❌ Wallet not backed up to Night Chain. Cannot send funds.',
      };
    }

    if (!transactionPreview) {
      return {
        success: false,
        message: '❌ No transaction preview found. Build transaction first.',
      };
    }

    if (!accessKey || accessKey.length < 4 || accessKey.length > 12) {
      return {
        success: false,
        message: '❌ Invalid access key. Must be 4-12 characters.',
      };
    }

    try {
      setLoading(true, 'Signing and broadcasting transaction...');

      const bridge = await getWalletBridge();
      const fromAddress = chain === 'cardano' ? addresses.cardano : addresses.bitcoin.segwit;

      // Build the transaction (retrieves seed from Night Chain internally)
      const unsignedTx = await bridge.buildTransaction(
        {
          chain,
          from: fromAddress,
          to: transactionPreview.to,
          amount: transactionPreview.amount,
        },
        nightBackupTxId,
        accessKey
      );

      // Sign and broadcast (retrieves seed again, then wipes)
      const txHash = await bridge.signAndBroadcastTransaction(
        unsignedTx,
        nightBackupTxId,
        accessKey
      );

      // Clear transaction preview
      set({ transactionPreview: null });

      const symbol = chain === 'cardano' ? 'ADA' : 'BTC';
      const explorerUrl = chain === 'cardano' 
        ? `https://cardanoscan.io/transaction/${txHash}`
        : `https://blockchair.com/bitcoin/transaction/${txHash}`;

      let message = '✅ **Transaction Sent!**\n\n';
      message += `**Amount:** ${transactionPreview.amount} ${symbol}\n`;
      message += `**To:** ${transactionPreview.to}\n`;
      message += `**TX Hash:** ${txHash.substring(0, 16)}...${txHash.substring(txHash.length - 8)}\n\n`;
      message += `🔍 [View on Explorer](${explorerUrl})\n\n`;
      message += `Your ${symbol} should arrive in a few minutes.`;

      return {
        success: true,
        message,
      };
    } catch (error: any) {
      // Check for common errors
      if (error.message.includes('access key')) {
        return {
          success: false,
          message: '❌ Incorrect access key. Please try again.',
        };
      }

      if (error.message.includes('insufficient')) {
        return {
          success: false,
          message: '❌ Insufficient balance. Check your balance and try again.',
        };
      }

      return {
        success: false,
        message: `❌ Transaction failed: ${error.message}`,
      };
    } finally {
      setLoading(false);
    }
  },
}));

// Initialize store with persisted data
(async () => {
  try {
    const stored = await chrome.storage.local.get([
      'walletState',
      'walletAddresses',
      'nightBackupTxId',
      'recoveryChallenge',
    ]);
    
    if (stored.walletState) {
      useWalletStore.setState({ walletState: stored.walletState });
    }
    
    if (stored.walletAddresses) {
      useWalletStore.setState({ addresses: stored.walletAddresses });
    }
    
    if (stored.nightBackupTxId) {
      useWalletStore.setState({ nightBackupTxId: stored.nightBackupTxId });
    }
    
    if (stored.recoveryChallenge) {
      useWalletStore.setState({ recoveryChallenge: stored.recoveryChallenge });
    }
  } catch (error) {
    console.error('Failed to load persisted wallet state:', error);
  }
})();
