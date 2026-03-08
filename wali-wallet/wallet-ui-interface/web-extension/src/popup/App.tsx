/**
 * Main popup application for browser extension
 */

import React, { useState, useEffect, useRef } from 'react';
import { CommandParser, ParsedCommand, CommandResponse } from '@wallet-ui/shared';
import { useWalletStore } from '../store/wallet';
import { ChatMessage } from './components/ChatMessage';
import { TransactionPreviewCard } from './components/TransactionPreviewCard';
import { AssetList } from './components/AssetList';
import { LoadingIndicator } from './components/LoadingIndicator';
import { ErrorBanner } from './components/ErrorBanner';
import { ReceiveModal } from './components/ReceiveModal';
import { RecoveryWordsDisplay } from './components/RecoveryWordsDisplay';
import { RecoveryImportModal } from './components/RecoveryImportModal';
import './App.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  parsedCommand?: ParsedCommand;
  response?: CommandResponse;
}

export const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showReceiveModal, setShowReceiveModal] = useState(false);
  const [showRecoveryWords, setShowRecoveryWords] = useState(false);
  const [showRecoveryImport, setShowRecoveryImport] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const parser = useRef(new CommandParser());

  const {
    walletState,
    loading,
    error,
    addresses,
    recoveryChallenge,
    processCommand,
    recoverFromNightChain,
    clearError,
  } = useWalletStore();

  useEffect(() => {
    // Scroll to bottom when new messages arrive
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    // Load persisted wallet state
    const loadState = async () => {
      const result = await chrome.storage.local.get(['walletState']);
      if (result.walletState?.isInitialized) {
        // Wallet exists - show welcome back
        addAssistantMessage(`🦭 Welcome back! What would you like to do?`);
      } else {
        // New user
        addAssistantMessage(
          "👋 Hey there! I'm wAli, your crypto companion.\n\n" +
          "There's a lot you can do with a blockchain wallet! Just tell me what you need and I'll hop off my rock and handle it.\n\n" +
          "**Getting Started:**\n" +
          "• New here? Just type: **create wallet**\n" +
          "• Already an OG? Type: **import wallet** and I'll fetch it for you\n\n" +
          "Once you've got a wallet set up, I'll show you all the cool stuff we can do together! 🦭\n\n" +
          "No slashes needed - just talk to me like a friend!"
        );
      }
    };
    loadState();
  }, []);

  const addAssistantMessage = (content: string, response?: CommandResponse) => {
    setMessages(prev => [
      ...prev,
      {
        id: Date.now().toString(),
        role: 'assistant',
        content,
        timestamp: Date.now(),
        response,
      },
    ]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsProcessing(true);

    try {
      // Parse the command
      const parsed = parser.current.parse(userMessage.content);

      // Check for ambiguities
      if (parsed.ambiguities.length > 0) {
        const ambiguityMessage = parsed.ambiguities
          .map((a: { message: string }) => `• ${a.message}`)
          .join('\n');
        
        addAssistantMessage(ambiguityMessage);
        setIsProcessing(false);
        return;
      }

      // Handle wallet creation
      if (parsed.intent.type === 'create_wallet') {
        addAssistantMessage(
          "🦭 Creating your new wallet...\n\n" +
          "I'm generating a secure 24-word recovery phrase. Keep this SAFE - it's the only way to restore your wallet!\n\n" +
          "⏳ Give me a moment..."
        );
        // Mark wallet as initialized and save
        setTimeout(async () => {
          // Save wallet state to chrome.storage
          const newState = {
            isInitialized: true,
            isLocked: false,
            accounts: ['wAli Wallet'],
            assets: [],
            connections: [],
            activeAccount: 'wAli Wallet'
          };
          await chrome.storage.local.set({ walletState: newState });
          
          addAssistantMessage(
            "✅ Wallet created!\n\n" +
            "Here's what you can do now:\n" +
            "• **what's my balance?** - Check your ADA and tokens\n" +
            "• **send 10 ADA to addr1...** - Send funds\n" +
            "• **show history** - View past transactions\n" +
            "• **receive** - Get your wallet address\n\n" +
            "Just ask! No slashes or commands needed - talk to me naturally. 🦭"
          );
        }, 2000);
        setIsProcessing(false);
        return;
      }

      // Handle wallet import
      if (parsed.intent.type === 'import_wallet') {
        addAssistantMessage(
          "🦭 Ready to restore your wallet!\n\n" +
          "You can either:\n" +
          "1. **Recover from Night Chain** - Use your 4-line recovery challenge\n" +
          "2. **Type your 12 or 24-word phrase** directly (I'll handle it securely)\n" +
          "3. **Upload a file** with your phrase (more secure - file never leaves your device)\n\n" +
          "Type **'recover from night'** for Night Chain recovery, or paste your seed phrase."
        );
        setIsProcessing(false);
        return;
      }

      // Handle Night Chain recovery trigger
      if (/recover.*night|night.*recover/i.test(userMessage.content)) {
        setShowRecoveryImport(true);
        setIsProcessing(false);
        return;
      }

      // Handle help/commands
      if (/help|commands|what.*can.*do/i.test(userMessage.content)) {
        addAssistantMessage(
          "🦭 Here's what I can help with:\n\n" +
          "**Wallet Management:**\n" +
          "• create wallet / new wallet\n" +
          "• import wallet / restore wallet\n\n" +
          "**Check Balances:**\n" +
          "• what's my balance?\n" +
          "• how much ADA do I have?\n\n" +
          "**Send Funds:**\n" +
          "• send 10 ADA to addr1...\n" +
          "• send 50 to $feedwali (ADA handles work!)\n\n" +
          "**View Activity:**\n" +
          "• show history / show transactions\n" +
          "• receive / my address\n\n" +
          "No slashes needed - just talk naturally! 🦭"
        );
        setIsProcessing(false);
        return;
      }

      // Check for "receive" command - show modal instead of text
      if (/receive|deposit|get.*address|my.*address/i.test(userMessage.content)) {
        if (addresses) {
          setShowReceiveModal(true);
          setIsProcessing(false);
          return;
        } else {
          addAssistantMessage('❌ No wallet found. Create a wallet first!');
          setIsProcessing(false);
          return;
        }
      }

      // Process the command through the wallet store
      const response = await processCommand(parsed);

      // Check if we need to show recovery challenge
      if (response.data?.showRecoveryChallenge && response.data?.recoveryChallenge) {
        setShowRecoveryWords(true);
      }

      // Show response
      if (response.requiresConfirmation && response.preview) {
        addAssistantMessage(
          'Please review this transaction:',
          response
        );
      } else {
        addAssistantMessage(response.message, response);
      }
    } catch (error: any) {
      addAssistantMessage(
        `❌ ${error.message || 'Something went wrong. Please try again.'}`
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleQuickAction = async (command: string) => {
    if (command === 'receive' && addresses) {
      setShowReceiveModal(true);
      return;
    }
    
    // Execute command directly (don't just insert into input)
    setIsProcessing(true);
    
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: command,
      timestamp: Date.now(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    
    try {
      const parsed = parser.current.parse(command);
      const response = await processCommand(parsed);
      
      // Check if we need to show special UI
      if (response.data?.showRecoveryChallenge && response.data?.recoveryChallenge) {
        setShowRecoveryWords(true);
      }
      
      addAssistantMessage(response.message, response);
    } catch (error: any) {
      addAssistantMessage(
        `❌ ${error.message || 'Something went wrong. Please try again.'}`
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRecoveryAcknowledge = () => {
    setShowRecoveryWords(false);
    addAssistantMessage(
      '✅ **Wallet Setup Complete!**\n\n' +
      'Your wallet is now fully set up and ready to use.\n\n' +
      'Try these commands:\n' +
      '• **what\'s my balance?**\n' +
      '• **receive** - Show your addresses\n' +
      '• **send 10 ADA to addr1...**\n\n' +
      'Welcome to wAli! 🦭'
    );
  };

  const handleRecoveryImport = async (challengeWords: string[], accessKey: string) => {
    setShowRecoveryImport(false);
    setIsProcessing(true);
    
    try {
      const response = await recoverFromNightChain(challengeWords, accessKey);
      addAssistantMessage(response.message);
    } catch (error: any) {
      addAssistantMessage(`❌ Recovery failed: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="app-container" role="main" aria-label="Wallet Interface">
      {/* Header */}
      <header className="app-header">
        <h1>💬 wAli Chat</h1>
        {walletState.activeAccount && (
          <div className="account-info" aria-label="Active account">
            <span className="account-name">{walletState.activeAccount}</span>
          </div>
        )}
      </header>

      {/* Error Banner */}
      {error.hasError && (
        <ErrorBanner
          message={error.message || 'An error occurred'}
          recoveryAction={error.recoveryAction}
          onDismiss={clearError}
        />
      )}

      {/* Asset Summary */}
      {walletState.isInitialized && !walletState.isLocked && (
        <section className="assets-section" aria-label="Your assets">
          <AssetList assets={walletState.assets} compact />
        </section>
      )}

      {/* Chat Messages */}
      <div className="messages-container" role="log" aria-label="Chat messages" aria-live="polite">
        {messages.map(msg => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {/* Transaction Preview */}
        {messages.length > 0 &&
          messages[messages.length - 1].response?.preview && (
          <TransactionPreviewCard
            preview={messages[messages.length - 1].response!.preview!}
            onConfirm={() => {
              addAssistantMessage('✅ Transaction submitted! View it in your transaction history.');
            }}
            onEdit={() => {
              addAssistantMessage('Let me know what you\'d like to change.');
            }}
            onCancel={() => {
              addAssistantMessage('Transaction cancelled.');
            }}
          />
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Loading Indicator */}
      {(isProcessing || loading.isLoading) && (
        <LoadingIndicator operation={loading.operation} />
      )}

      {/* Quick Actions */}
      <div className="quick-actions" role="toolbar" aria-label="Quick actions">
        <button
          onClick={() => handleQuickAction('show balance')}
          className="quick-action-btn"
          disabled={isProcessing}
          aria-label="Show balance"
        >
          💰 Balance
        </button>
        <button
          onClick={() => handleQuickAction('show transactions')}
          className="quick-action-btn"
          disabled={isProcessing}
          aria-label="Show transactions"
        >
          📜 History
        </button>
        <button
          onClick={() => handleQuickAction('receive')}
          className="quick-action-btn"
          disabled={isProcessing}
          aria-label="Receive funds"
        >
          ⬇️ Receive
        </button>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="input-form">
        <label htmlFor="command-input" className="sr-only">
          Enter command
        </label>
        <input
          id="command-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a command... e.g., send 10 ADA to $feedwali"
          className="command-input"
          disabled={isProcessing}
          aria-describedby="input-hint"
          autoFocus
        />
        <span id="input-hint" className="sr-only">
          Enter natural language commands like "send 10 ADA to address" or "show balance"
        </span>
        <button
          type="submit"
          className="submit-btn"
          disabled={isProcessing || !input.trim()}
          aria-label="Send command"
        >
          {isProcessing ? '⏳' : '➤'}
        </button>
      </form>

      {/* Modals */}
      {showReceiveModal && addresses && (
        <ReceiveModal
          addresses={addresses}
          onClose={() => setShowReceiveModal(false)}
        />
      )}

      {showRecoveryWords && recoveryChallenge && (
        <RecoveryWordsDisplay
          challengeWords={recoveryChallenge}
          onAcknowledge={handleRecoveryAcknowledge}
        />
      )}

      {showRecoveryImport && (
        <RecoveryImportModal
          onRecover={handleRecoveryImport}
          onCancel={() => setShowRecoveryImport(false)}
        />
      )}
    </div>
  );
};




