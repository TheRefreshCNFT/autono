/**
 * wAli - Your Friendly Crypto Companion 🦭
 * Web Extension Main App
 */

import React, { useState, useEffect, useRef } from 'react';
import { CommandParser, ParsedCommand, CommandResponse, WaliPersonality, WaliResponse } from '@wallet-ui/shared';
import { useWalletStore } from '../store/wallet';
import { ChatMessage } from './components/ChatMessage';
import { TransactionPreviewCard } from './components/TransactionPreviewCard';
import { AssetList } from './components/AssetList';
import { LoadingIndicator } from './components/LoadingIndicator';
import { ErrorBanner } from './components/ErrorBanner';
import './WaliApp.css';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'wali';
  content: string;
  timestamp: number;
  parsedCommand?: ParsedCommand;
  response?: CommandResponse;
  waliResponse?: WaliResponse;
}

export const WaliApp: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const parser = useRef(new CommandParser());
  const wali = useRef(new WaliPersonality());

  const {
    walletState,
    loading,
    error,
    processCommand,
    clearError,
  } = useWalletStore();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    // wAli's welcome message based on wallet state
    if (!walletState.isInitialized) {
      const welcomeMsg = wali.current.welcome('new');
      addWaliMessage(welcomeMsg);
    } else if (walletState.isLocked) {
      const lockedMsg = wali.current.welcome('locked');
      addWaliMessage(lockedMsg);
    } else {
      const returningMsg = wali.current.welcome('returning');
      addWaliMessage(returningMsg);
      
      // Show balance info
      if (walletState.assets.length > 0) {
        const balanceMsg = wali.current.balance(true, walletState.assets.length);
        setTimeout(() => addWaliMessage(balanceMsg), 500);
      }
    }
  }, []);

  const addWaliMessage = (waliResponse: WaliResponse, commandResponse?: CommandResponse) => {
    setMessages(prev => [
      ...prev,
      {
        id: Date.now().toString() + Math.random(),
        role: 'wali',
        content: waliResponse.message,
        timestamp: Date.now(),
        waliResponse,
        response: commandResponse,
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
    const userInput = input.trim();
    setInput('');
    setIsProcessing(true);

    try {
      // Check for help commands
      if (/^(help|what can you do|commands)$/i.test(userInput)) {
        addWaliMessage(wali.current.help());
        setIsProcessing(false);
        return;
      }

      // Check for wallet creation
      if (/^(create|new|setup).*(wallet)$/i.test(userInput)) {
        addWaliMessage(wali.current.walletCreation('starting'));
        setIsProcessing(false);
        return;
      }

      // Parse the command
      const parsed = parser.current.parse(userInput);

      // Check for ambiguities
      if (parsed.ambiguities.length > 0) {
        const ambiguityMessage: WaliResponse = {
          type: 'warning',
          emoji: '🤔',
          message: 'Hmm, I need a bit more info:\n' + parsed.ambiguities
            .map((a: { message: string }) => `• ${a.message}`)
            .join('\n'),
          suggestions: parsed.ambiguities[0].suggestions
        };
        
        addWaliMessage(ambiguityMessage);
        setIsProcessing(false);
        return;
      }

      // Show building transaction
      if (parsed.intent.type === 'send') {
        addWaliMessage(wali.current.transaction('building'));
      }

      // Process the command through the wallet store
      const response = await processCommand(parsed);

      // Show wAli response based on result
      if (response.requiresConfirmation && response.preview) {
        addWaliMessage(wali.current.transaction('reviewing'), response);
      } else if (response.success) {
        if (parsed.intent.metadata?.query === 'balance') {
          addWaliMessage(wali.current.balance(
            walletState.assets.length > 0,
            walletState.assets.length
          ));
        } else {
          addWaliMessage({
            type: 'success',
            emoji: '✅',
            message: response.message
          }, response);
        }
      } else {
        addWaliMessage({
          type: 'error',
          emoji: '😕',
          message: wali.current.transaction('failed', { error: response.message }).message
        });
      }
    } catch (error: any) {
      addWaliMessage({
        type: 'error',
        emoji: '😅',
        message: `Oops! ${wali.current.transaction('failed', { error }).message}`,
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleConfirmTransaction = async () => {
    setIsProcessing(true);
    
    addWaliMessage(wali.current.transaction('signing'));
    
    // Simulate transaction signing and broadcasting
    setTimeout(() => {
      addWaliMessage(wali.current.transaction('broadcasting'));
      
      setTimeout(() => {
        addWaliMessage(wali.current.transaction('sent', { 
          txHash: 'abc123def456...' 
        }));
        setIsProcessing(false);
      }, 1500);
    }, 1000);
  };

  const handleQuickAction = (command: string) => {
    setInput(command);
  };

  return (
    <div className="wali-app-container" role="main" aria-label="wAli Wallet Interface">
      {/* Header with wAli branding */}
      <header className="wali-header">
        <div className="wali-logo">
          <span className="wali-logo-icon">🦭</span>
          <h1 className="wali-title">wAli</h1>
        </div>
        <p className="wali-tagline">Your crypto companion</p>
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
      {walletState.isInitialized && !walletState.isLocked && walletState.assets.length > 0 && (
        <section className="assets-section" aria-label="Your assets">
          <h2 className="section-title">💰 Your Assets</h2>
          <AssetList assets={walletState.assets} compact />
        </section>
      )}

      {/* Chat Messages */}
      <div className="messages-container" role="log" aria-label="Chat messages" aria-live="polite">
        {messages.map(msg => (
          <div key={msg.id} className={`message-wrapper message-${msg.role}`}>
            {msg.role === 'wali' && (
              <div className="wali-avatar" aria-label="wAli">🦭</div>
            )}
            <div className="message-content">
              {msg.waliResponse?.emoji && (
                <span className="message-emoji">{msg.waliResponse.emoji}</span>
              )}
              <ChatMessage message={msg} />
              {msg.waliResponse?.suggestions && msg.waliResponse.suggestions.length > 0 && (
                <div className="message-suggestions">
                  {msg.waliResponse.suggestions.map((suggestion: string, idx: number) => (
                    <button
                      key={idx}
                      className="suggestion-btn"
                      onClick={() => handleQuickAction(suggestion)}
                      disabled={isProcessing}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Transaction Preview */}
        {messages.length > 0 &&
          messages[messages.length - 1].response?.preview && (
          <TransactionPreviewCard
            preview={messages[messages.length - 1].response!.preview!}
            onConfirm={handleConfirmTransaction}
            onEdit={() => {
              addWaliMessage({
                type: 'info',
                emoji: '✏️',
                message: 'What would you like to change?',
                suggestions: ['Change amount', 'Different address', 'Cancel']
              });
            }}
            onCancel={() => {
              addWaliMessage({
                type: 'info',
                emoji: '👍',
                message: 'Transaction cancelled. No worries!',
              });
            }}
          />
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Loading Indicator */}
      {(isProcessing || loading.isLoading) && (
        <LoadingIndicator operation={loading.operation || 'Processing...'} />
      )}

      {/* Quick Actions */}
      <div className="quick-actions" role="toolbar" aria-label="Quick actions">
        <button
          onClick={() => handleQuickAction('show balance')}
          className="quick-action-btn"
          disabled={isProcessing || walletState.isLocked}
          aria-label="Show balance"
        >
          💰 Balance
        </button>
        <button
          onClick={() => handleQuickAction('show transactions')}
          className="quick-action-btn"
          disabled={isProcessing || walletState.isLocked}
          aria-label="Show transactions"
        >
          📜 History
        </button>
        <button
          onClick={() => handleQuickAction('receive')}
          className="quick-action-btn"
          disabled={isProcessing || walletState.isLocked}
          aria-label="Receive funds"
        >
          ⬇️ Receive
        </button>
        <button
          onClick={() => handleQuickAction('help')}
          className="quick-action-btn help-btn"
          disabled={isProcessing}
          aria-label="Help"
        >
          ❓ Help
        </button>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="input-form">
        <label htmlFor="command-input" className="sr-only">
          Talk to wAli
        </label>
        <input
          id="command-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Talk to wAli... e.g., send 10 ADA to $feedwali"
          className="command-input"
          disabled={isProcessing || walletState.isLocked}
          aria-describedby="input-hint"
          autoFocus
        />
        <span id="input-hint" className="sr-only">
          Talk to wAli naturally, like "send 10 ADA to address" or "show my balance"
        </span>
        <button
          type="submit"
          className="submit-btn"
          disabled={isProcessing || !input.trim() || walletState.isLocked}
          aria-label="Send message"
          title="Send"
        >
          {isProcessing ? '⏳' : '🦭'}
        </button>
      </form>

      {/* Footer */}
      <footer className="wali-footer">
        <small>wAli • Making crypto friendly since 2026 🦭</small>
      </footer>
    </div>
  );
};

export default WaliApp;
