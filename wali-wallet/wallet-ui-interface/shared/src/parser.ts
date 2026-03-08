/**
 * Natural language command parser for wallet operations
 */

import {
  ParsedCommand,
  TransactionIntent,
  Ambiguity,
  Chain,
  Address,
  Asset,
} from './types';

export class CommandParser {
  private readonly sendPatterns = [
    /^send\s+(\d+\.?\d*)\s+(\w+)\s+to\s+(.+)$/i,
    /^send\s+(\d+\.?\d*)\s+to\s+(.+)$/i,
    /^transfer\s+(\d+\.?\d*)\s+(\w+)\s+to\s+(.+)$/i,
    /^pay\s+(.+)\s+(\d+\.?\d*)\s+(\w+)$/i,
    /^give\s+(\d+\.?\d*)\s+(\w+)\s+to\s+(.+)$/i,
    /^move\s+(\d+\.?\d*)\s+(\w+)\s+to\s+(.+)$/i,
  ];

  private readonly handlePattern = /^\$[\w-]+$/;
  private readonly cardanoAddrPattern = /^addr1[a-z0-9]{58,}$/i;
  private readonly bitcoinAddrPattern = /^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,87}$/;

  /**
   * Parse a natural language command into a structured transaction intent
   */
  parse(input: string): ParsedCommand {
    const trimmed = input.trim();
    const ambiguities: Ambiguity[] = [];

    // Try to parse as send command
    const sendIntent = this.parseSendCommand(trimmed, ambiguities);
    if (sendIntent) {
      return {
        intent: sendIntent,
        confidence: this.calculateConfidence(sendIntent, ambiguities),
        ambiguities,
        rawInput: input,
      };
    }

    // Wallet creation
    if (/create|new|make|setup|start|build|generate/i.test(trimmed) && /wallet/i.test(trimmed)) {
      return {
        intent: { type: 'create_wallet', chain: 'cardano' },
        confidence: 1.0,
        ambiguities: [],
        rawInput: input,
      };
    }

    // Wallet import/restore
    if (/import|restore|recover|load/i.test(trimmed) && /wallet|seed|phrase|mnemonic/i.test(trimmed)) {
      return {
        intent: { type: 'import_wallet', chain: 'cardano' },
        confidence: 1.0,
        ambiguities: [],
        rawInput: input,
      };
    }

    // Balance queries
    if (/balance|funds|money|how much|what.?s.*my/i.test(trimmed)) {
      return {
        intent: { type: 'show_balance', chain: 'cardano' },
        confidence: 1.0,
        ambiguities: [],
        rawInput: input,
      };
    }

    // Transaction history
    if (/history|transactions|activity|recent|past|previous/i.test(trimmed)) {
      return {
        intent: { type: 'show_history', chain: 'cardano' },
        confidence: 1.0,
        ambiguities: [],
        rawInput: input,
      };
    }

    // Receive
    if (/receive|deposit|get.*address|my.*address|where.*send/i.test(trimmed)) {
      return {
        intent: { type: 'show_balance', chain: 'cardano', metadata: { showAddress: true } },
        confidence: 1.0,
        ambiguities: [],
        rawInput: input,
      };
    }

    // Try to parse as balance query
    const balanceIntent = this.parseBalanceQuery(trimmed, ambiguities);
    if (balanceIntent) {
      return {
        intent: balanceIntent,
        confidence: this.calculateConfidence(balanceIntent, ambiguities),
        ambiguities,
        rawInput: input,
      };
    }

    // Unknown command
    ambiguities.push({
      field: 'command',
      message: 'I didn\'t quite catch that. Here are some things I can help with:',
      suggestions: [
        'create a new wallet',
        'send 10 ADA to addr1...',
        'what\'s my balance?',
        'show my transaction history',
        'where can I receive funds?',
      ],
    });

    return {
      intent: { type: 'send', chain: 'cardano' },
      confidence: 0,
      ambiguities,
      rawInput: input,
    };
  }

  private parseSendCommand(input: string, ambiguities: Ambiguity[]): TransactionIntent | null {
    for (const pattern of this.sendPatterns) {
      const match = input.match(pattern);
      if (match) {
        return this.extractSendIntent(match, ambiguities);
      }
    }
    return null;
  }

  private extractSendIntent(match: RegExpMatchArray, ambiguities: Ambiguity[]): TransactionIntent {
    let amount: string | undefined;
    let symbol: string | undefined;
    let recipient: string | undefined;

    // Pattern: send <amount> <symbol> to <recipient>
    if (match.length === 4) {
      amount = match[1];
      symbol = match[2];
      recipient = match[3];
    }
    // Pattern: send <amount> to <recipient> (missing symbol)
    else if (match.length === 3) {
      amount = match[1];
      recipient = match[2];
      ambiguities.push({
        field: 'asset',
        message: `Send ${amount} of what token?`,
        suggestions: ['ADA', 'BTC', 'USDT', 'HOSKY'],
      });
    }

    const intent: TransactionIntent = {
      type: 'send',
      chain: this.inferChain(symbol, recipient),
      amount,
    };

    // Parse recipient
    if (recipient) {
      const address = this.parseAddress(recipient, intent.chain, ambiguities);
      if (address) {
        intent.to = address;
      }
    }

    // Parse asset
    if (symbol) {
      intent.asset = this.parseAsset(symbol, intent.chain, ambiguities);
    }

    return intent;
  }

  private parseBalanceQuery(input: string, ambiguities: Ambiguity[]): TransactionIntent | null {
    const balancePatterns = [
      /^(show|display|check|view)\s+(my\s+)?balance$/i,
      /^balance$/i,
      /^how much .+ do i have/i,
    ];

    for (const pattern of balancePatterns) {
      if (pattern.test(input)) {
        // Balance queries are read-only, we'll use 'send' type with metadata flag
        return {
          type: 'send',
          chain: 'cardano',
          metadata: { query: 'balance' },
        };
      }
    }

    return null;
  }

  private parseAddress(input: string, chain: Chain, ambiguities: Ambiguity[]): Address | null {
    // Check for handle format
    if (this.handlePattern.test(input)) {
      return {
        address: input,
        type: 'handle',
        chain,
        metadata: { handle: input },
      };
    }

    // Check for Cardano address
    if (this.cardanoAddrPattern.test(input)) {
      return {
        address: input,
        type: 'address',
        chain: 'cardano',
      };
    }

    // Check for Bitcoin address
    if (this.bitcoinAddrPattern.test(input)) {
      return {
        address: input,
        type: 'address',
        chain: 'bitcoin',
      };
    }

    ambiguities.push({
      field: 'recipient',
      message: `"${input}" doesn't look like a valid address or handle. Please check and try again.`,
      suggestions: ['Use a valid addr1... address', 'Use a $handle', 'Use a Bitcoin address'],
    });

    return null;
  }

  private parseAsset(symbol: string, chain: Chain, ambiguities: Ambiguity[]): Asset | undefined {
    const upperSymbol = symbol.toUpperCase();

    // Known native assets
    const nativeAssets: Record<string, Partial<Asset>> = {
      'ADA': { chain: 'cardano', type: 'native', decimals: 6 },
      'BTC': { chain: 'bitcoin', type: 'native', decimals: 8 },
      'TBTC': { chain: 'bitcoin', type: 'native', decimals: 8 },
    };

    if (nativeAssets[upperSymbol]) {
      return {
        symbol: upperSymbol,
        balance: '0',
        ...nativeAssets[upperSymbol],
      } as Asset;
    }

    // Unknown asset - could be a token
    ambiguities.push({
      field: 'asset',
      message: `I haven't heard of "${symbol}". Is this a token you hold?`,
      suggestions: ['Check the spelling', 'Make sure you own this token', 'Try ADA or BTC'],
    });

    return {
      chain,
      type: 'token',
      symbol: upperSymbol,
      decimals: 0,
      balance: '0',
    };
  }

  private inferChain(symbol?: string, recipient?: string): Chain {
    if (symbol) {
      const upper = symbol.toUpperCase();
      if (upper === 'BTC' || upper === 'TBTC') return 'bitcoin';
      if (upper === 'ADA') return 'cardano';
    }

    if (recipient) {
      if (this.bitcoinAddrPattern.test(recipient)) return 'bitcoin';
      if (this.cardanoAddrPattern.test(recipient)) return 'cardano';
    }

    return 'cardano'; // Default
  }

  private calculateConfidence(intent: TransactionIntent, ambiguities: Ambiguity[]): number {
    let confidence = 100;

    // Reduce confidence for each ambiguity
    confidence -= ambiguities.length * 25;

    // Reduce if missing critical fields
    if (intent.type === 'send') {
      if (!intent.to) confidence -= 30;
      if (!intent.amount) confidence -= 30;
      if (!intent.asset) confidence -= 20;
    }

    return Math.max(0, Math.min(100, confidence));
  }
}
