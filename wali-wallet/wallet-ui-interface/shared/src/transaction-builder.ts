/**
 * Transaction preview builder
 * Integrates with wallet-core-engine for actual transaction construction
 */

import {
  TransactionIntent,
  TransactionPreview,
  Asset,
} from './types';

export interface WalletCoreEngine {
  estimateFee(intent: TransactionIntent): Promise<{ fee: string; feeAsset: Asset }>;
  buildTransaction(intent: TransactionIntent): Promise<any>;
  validateTransaction(intent: TransactionIntent): Promise<{ valid: boolean; warnings: string[] }>;
}

export class TransactionBuilder {
  constructor(private coreEngine: WalletCoreEngine) {}

  /**
   * Build a human-readable transaction preview
   */
  async buildPreview(intent: TransactionIntent): Promise<TransactionPreview> {
    // Validate transaction
    const validation = await this.coreEngine.validateTransaction(intent);
    
    // Estimate fee
    const { fee, feeAsset } = await this.coreEngine.estimateFee(intent);

    // Calculate total cost
    const totalCost = this.calculateTotalCost(intent, fee, feeAsset);

    // Generate human-readable description
    const humanReadable = this.generateHumanReadable(intent, fee, feeAsset);

    return {
      intent,
      fee,
      feeAsset,
      totalCost,
      humanReadable,
      warnings: validation.warnings,
    };
  }

  private calculateTotalCost(intent: TransactionIntent, fee: string, feeAsset: Asset): string {
    if (intent.type === 'send' && intent.asset && intent.amount) {
      // If sending the same asset as fee, add them
      if (intent.asset.symbol === feeAsset.symbol) {
        const amount = parseFloat(intent.amount);
        const feeAmount = parseFloat(fee);
        return (amount + feeAmount).toFixed(intent.asset.decimals);
      }
      // Different assets, just return the send amount
      return intent.amount;
    }
    return fee;
  }

  private generateHumanReadable(intent: TransactionIntent, fee: string, feeAsset: Asset): string {
    const parts: string[] = [];

    switch (intent.type) {
      case 'send':
        if (intent.amount && intent.asset && intent.to) {
          parts.push(`Send ${intent.amount} ${intent.asset.symbol}`);
          
          if (intent.to.type === 'handle') {
            parts.push(`to ${intent.to.metadata?.handle || intent.to.address}`);
          } else {
            const shortAddr = this.shortenAddress(intent.to.address);
            parts.push(`to ${shortAddr}`);
          }
        }
        break;

      case 'delegate':
        parts.push('Delegate stake');
        if (intent.metadata?.poolId) {
          parts.push(`to pool ${intent.metadata.poolId.slice(0, 8)}...`);
        }
        break;

      case 'swap':
        parts.push('Swap tokens');
        break;

      default:
        parts.push(`${intent.type} transaction`);
    }

    parts.push(`\n\nNetwork fee: ${fee} ${feeAsset.symbol}`);

    if (intent.metadata?.memo) {
      parts.push(`\nMemo: ${intent.metadata.memo}`);
    }

    return parts.join(' ');
  }

  private shortenAddress(address: string): string {
    if (address.length <= 20) return address;
    return `${address.slice(0, 8)}...${address.slice(-6)}`;
  }

  /**
   * Generate explanation for dApp transaction requests
   */
  generateDAppExplanation(intent: TransactionIntent, dappName: string): string {
    const explanation: string[] = [`${dappName} is requesting:`];

    switch (intent.type) {
      case 'send':
        if (intent.amount && intent.asset) {
          explanation.push(`• Send ${intent.amount} ${intent.asset.symbol}`);
        }
        if (intent.to) {
          explanation.push(`• To: ${intent.to.type === 'handle' ? intent.to.metadata?.handle : this.shortenAddress(intent.to.address)}`);
        }
        break;

      case 'delegate':
        explanation.push(`• Delegate your stake`);
        break;

      case 'swap':
        explanation.push(`• Execute a token swap`);
        break;

      case 'mint':
        explanation.push(`• Mint new tokens or NFTs`);
        break;

      default:
        explanation.push(`• Execute a ${intent.type} transaction`);
    }

    explanation.push('\n⚠️ Only approve if you trust this application and understand what you\'re signing.');

    return explanation.join('\n');
  }
}
