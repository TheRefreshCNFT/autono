/**
 * wAli Personality Module 🦭
 * 
 * Adds friendly, conversational responses to wallet operations.
 * Makes crypto simple and approachable, not scary.
 */

export interface WaliResponse {
  message: string;
  type: 'welcome' | 'success' | 'error' | 'info' | 'warning' | 'thinking';
  emoji?: string;
  suggestions?: string[];
}

/**
 * wAli's friendly personality engine
 */
export class WaliPersonality {
  private userName?: string;

  constructor(userName?: string) {
    this.userName = userName;
  }

  setUserName(name: string) {
    this.userName = name;
  }

  /**
   * Welcome messages for different contexts
   */
  welcome(context: 'new' | 'returning' | 'locked' | 'restored'): WaliResponse {
    const greetings = [
      `Hey${this.userName ? ` ${this.userName}` : ''}! 👋`,
      `Hi there${this.userName ? ` ${this.userName}` : ''}! 🦭`,
      `Welcome${this.userName ? ` back ${this.userName}` : ''}! ✨`,
    ];

    const greeting = greetings[Math.floor(Math.random() * greetings.length)];

    switch (context) {
      case 'new':
        return {
          type: 'welcome',
          emoji: '🦭',
          message: `${greeting} I'm wAli, your crypto companion! Ready to create your first wallet? It's easier than ordering coffee.`,
          suggestions: [
            'Create a new wallet',
            'Restore existing wallet',
            'Tell me more about wAli'
          ]
        };

      case 'returning':
        return {
          type: 'welcome',
          emoji: '✨',
          message: `${greeting} What can I help you with today?`,
          suggestions: [
            'Show my balance',
            'Send some crypto',
            'View transaction history',
            'Connect to a dApp'
          ]
        };

      case 'locked':
        return {
          type: 'warning',
          emoji: '🔒',
          message: `Your wallet is locked. Enter your access key to unlock it and we'll get back to business!`
        };

      case 'restored':
        return {
          type: 'success',
          emoji: '🎉',
          message: `${greeting} Your wallet is back! Everything's right where you left it.`,
          suggestions: [
            'Show my balance',
            'What\'s new?'
          ]
        };

      default:
        return {
          type: 'welcome',
          emoji: '🦭',
          message: greeting
        };
    }
  }

  /**
   * Transaction-related responses
   */
  transaction(action: 'building' | 'reviewing' | 'signing' | 'broadcasting' | 'sent' | 'failed', details?: any): WaliResponse {
    switch (action) {
      case 'building':
        return {
          type: 'thinking',
          emoji: '🔨',
          message: 'Building your transaction... This\'ll just take a sec!'
        };

      case 'reviewing':
        return {
          type: 'info',
          emoji: '🔍',
          message: 'Here\'s what you\'re about to send. Look good?',
          suggestions: ['Confirm', 'Edit', 'Cancel']
        };

      case 'signing':
        return {
          type: 'thinking',
          emoji: '✍️',
          message: 'Signing the transaction securely...'
        };

      case 'broadcasting':
        return {
          type: 'thinking',
          emoji: '📡',
          message: 'Sending to the network...'
        };

      case 'sent':
        return {
          type: 'success',
          emoji: '🚀',
          message: `Transaction sent! ${details?.txHash ? `\n\nTrack it: ${details.txHash.substring(0, 16)}...` : ''}`,
          suggestions: ['View in explorer', 'Send another', 'Done']
        };

      case 'failed':
        return {
          type: 'error',
          emoji: '😕',
          message: `Hmm, that didn't work. ${this.explainError(details?.error)}`,
          suggestions: ['Try again', 'Check balance', 'Get help']
        };

      default:
        return {
          type: 'info',
          emoji: '💭',
          message: 'Processing transaction...'
        };
    }
  }

  /**
   * Wallet creation flow responses
   */
  walletCreation(step: 'starting' | 'generating' | 'encrypting' | 'storing' | 'complete' | 'error', details?: any): WaliResponse {
    switch (step) {
      case 'starting':
        return {
          type: 'info',
          emoji: '🎬',
          message: 'Alright! Let\'s create your wallet. First, choose an access key (4-12 characters).',
          suggestions: ['What\'s an access key?']
        };

      case 'generating':
        return {
          type: 'thinking',
          emoji: '🎲',
          message: 'Generating your secret recovery phrase... (This is the magic part!)'
        };

      case 'encrypting':
        return {
          type: 'thinking',
          emoji: '🔐',
          message: 'Encrypting with military-grade security... (Fancy, right?)'
        };

      case 'storing':
        return {
          type: 'thinking',
          emoji: '⛓️',
          message: 'Storing on the Night blockchain... (Your secrets are going into the vault!)'
        };

      case 'complete':
        return {
          type: 'success',
          emoji: '🎉',
          message: `Boom! Your wallet is ready! 🦭\n\n${details?.addresses ? `Your addresses:\n${this.formatAddresses(details.addresses)}` : ''}\n\n⚠️ Important: Save your Asset ID: ${details?.assetId}\n\nYou'll need this and your access key to recover your wallet.`,
          suggestions: ['Copy Asset ID', 'View recovery info', 'Start using wallet']
        };

      case 'error':
        return {
          type: 'error',
          emoji: '😅',
          message: `Oops! Something went wrong: ${this.explainError(details?.error)}`,
          suggestions: ['Try again', 'Get help']
        };

      default:
        return {
          type: 'thinking',
          emoji: '⏳',
          message: 'Creating your wallet...'
        };
    }
  }

  /**
   * Balance and asset responses
   */
  balance(hasAssets: boolean, assetCount?: number): WaliResponse {
    if (!hasAssets) {
      return {
        type: 'info',
        emoji: '👛',
        message: 'Your wallet is empty right now. Ready to receive some crypto?',
        suggestions: ['Show my address', 'Get testnet tokens', 'Learn about assets']
      };
    }

    return {
      type: 'info',
      emoji: '💰',
      message: `You have ${assetCount || 'several'} asset${assetCount !== 1 ? 's' : ''} in your wallet.`,
      suggestions: ['Send', 'Receive', 'View details']
    };
  }

  /**
   * Error explanations in human terms
   */
  private explainError(error: any): string {
    const message = error?.message || error || '';

    if (message.includes('insufficient')) {
      return 'You don\'t have enough funds for this transaction. (Check your balance!)';
    }

    if (message.includes('invalid address')) {
      return 'That address doesn\'t look right. Double-check it?';
    }

    if (message.includes('network')) {
      return 'Network hiccup! Try again in a moment.';
    }

    if (message.includes('denied') || message.includes('rejected')) {
      return 'Transaction was cancelled. No worries!';
    }

    if (message.includes('timeout')) {
      return 'That took too long. The network might be slow right now.';
    }

    if (message.includes('locked')) {
      return 'Too many wrong attempts. Your wallet is locked for security.';
    }

    // Generic friendly error
    return message || 'Something unexpected happened. Want to try again?';
  }

  /**
   * Format addresses nicely
   */
  private formatAddresses(addresses: any): string {
    const parts: string[] = [];

    if (addresses.cardano) {
      parts.push(`Cardano: ${addresses.cardano.substring(0, 20)}...`);
    }

    if (addresses.bitcoin) {
      parts.push(`Bitcoin: ${addresses.bitcoin}`);
    }

    return parts.join('\n');
  }

  /**
   * DApp connection responses
   */
  dappConnection(action: 'requesting' | 'approved' | 'rejected' | 'disconnected', dappName?: string): WaliResponse {
    switch (action) {
      case 'requesting':
        return {
          type: 'warning',
          emoji: '🔌',
          message: `${dappName || 'A dApp'} wants to connect to your wallet. Trust this one?`,
          suggestions: ['Approve', 'Reject', 'View permissions']
        };

      case 'approved':
        return {
          type: 'success',
          emoji: '✅',
          message: `Connected to ${dappName || 'the dApp'}! You can use it now.`
        };

      case 'rejected':
        return {
          type: 'info',
          emoji: '🚫',
          message: `Rejected connection to ${dappName || 'the dApp'}. Better safe than sorry!`
        };

      case 'disconnected':
        return {
          type: 'info',
          emoji: '🔌',
          message: `Disconnected from ${dappName || 'the dApp'}.`
        };

      default:
        return {
          type: 'info',
          emoji: '🔌',
          message: 'Managing dApp connection...'
        };
    }
  }

  /**
   * Recovery dialog responses
   */
  recovery(step: 'starting' | 'challenge' | 'unlocking' | 'success' | 'failed', remaining?: number): WaliResponse {
    switch (step) {
      case 'starting':
        return {
          type: 'info',
          emoji: '🔍',
          message: 'Let\'s recover your wallet! I\'ll ask you a few questions to make sure it\'s really you.',
          suggestions: ['Start recovery']
        };

      case 'challenge':
        return {
          type: 'info',
          emoji: '💭',
          message: 'Answer honestly - only you know these!',
        };

      case 'unlocking':
        return {
          type: 'thinking',
          emoji: '🔓',
          message: 'Unlocking your wallet...'
        };

      case 'success':
        return {
          type: 'success',
          emoji: '🎉',
          message: 'Welcome back! Your wallet is restored. 🦭',
          suggestions: ['Show balance', 'View transactions']
        };

      case 'failed':
        return {
          type: 'error',
          emoji: '❌',
          message: `Hmm, that didn't match.${remaining !== undefined ? ` You have ${remaining} attempt${remaining !== 1 ? 's' : ''} left.` : ''}`,
          suggestions: remaining && remaining > 0 ? ['Try again'] : ['Contact support']
        };

      default:
        return {
          type: 'info',
          emoji: '🔑',
          message: 'Recovering wallet...'
        };
    }
  }

  /**
   * Help and tips
   */
  help(topic?: string): WaliResponse {
    if (topic === 'access-key') {
      return {
        type: 'info',
        emoji: '🔑',
        message: 'Your access key is like a password that unlocks your encrypted wallet. Pick something memorable but secure! (4-12 characters)',
        suggestions: ['Create wallet', 'Back']
      };
    }

    if (topic === 'recovery') {
      return {
        type: 'info',
        emoji: '🆘',
        message: 'To recover your wallet, you\'ll need:\n1. Your Asset ID (saved during setup)\n2. Answers to your recovery questions\n3. Your access key\n\nKeep these safe!',
        suggestions: ['Start recovery', 'Back']
      };
    }

    return {
      type: 'info',
      emoji: '💡',
      message: 'I\'m wAli, your friendly crypto wallet! I can help you:\n• Create & manage wallets\n• Send & receive crypto\n• Connect to dApps\n• Keep your assets safe\n\nJust talk to me naturally!',
      suggestions: [
        'Show balance',
        'Send crypto',
        'View history',
        'Connect dApp'
      ]
    };
  }
}

export default WaliPersonality;
