/**
 * Wallet state management for mobile app
 * Same structure as web extension for consistency
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

interface WalletStore {
  walletState: WalletState;
  loading: LoadingState;
  error: ErrorState;
  
  processCommand: (command: ParsedCommand) => Promise<CommandResponse>;
  clearError: () => void;
  setLoading: (loading: boolean, operation?: string) => void;
}

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

  processCommand: async (command: ParsedCommand): Promise<CommandResponse> => {
    const { setLoading } = get();
    
    try {
      setLoading(true, 'Processing command...');

      // Simulate processing (integrate with wallet-core-engine)
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Mock response
      if (command.intent.type === 'send') {
        const preview: TransactionPreview = {
          intent: command.intent,
          fee: '0.17',
          feeAsset: {
            chain: 'cardano',
            type: 'native',
            symbol: 'ADA',
            decimals: 6,
            balance: '0',
          },
          totalCost: command.intent.amount ? 
            (parseFloat(command.intent.amount) + 0.17).toFixed(6) : '0.17',
          humanReadable: 'Send transaction',
          warnings: [],
        };

        return {
          success: true,
          message: 'Transaction ready for review',
          requiresConfirmation: true,
          preview,
        };
      }

      return {
        success: true,
        message: 'Command processed successfully',
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
    } finally {
      setLoading(false);
    }
  },

  clearError: () => {
    set({ error: { hasError: false } });
  },

  setLoading: (isLoading: boolean, operation?: string) => {
    set({ loading: { isLoading, operation } });
  },
}));
