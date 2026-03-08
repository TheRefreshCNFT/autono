/**
 * Payment Processor
 * Handles payment processing for dApp integrations and advertisements
 * Supports both Cardano native payments and traditional fiat
 */

import crypto from 'crypto';
import { PaymentTransaction } from './types';

export interface PaymentProcessorConfig {
  // Cardano settings
  cardanoEnabled?: boolean;
  cardanoPaymentAddress?: string;
  cardanoNetwork?: 'mainnet' | 'testnet';
  
  // Fiat payment settings (Stripe, etc.)
  fiatEnabled?: boolean;
  stripeApiKey?: string;
  
  // Webhook settings
  webhookUrl?: string;
  webhookSecret?: string;
  
  // Confirmation requirements
  minCardanoConfirmations?: number;
  
  // Exchange rate (for ADA <-> USD conversion)
  adaUsdRate?: number;
}

export interface PaymentIntent {
  intentId: string;
  dappId?: string;
  advertiserId?: string;
  
  amount: number;
  currency: 'USD' | 'ADA';
  
  description?: string;
  
  // Cardano payment details
  cardanoPaymentAddress?: string;
  expectedAmount?: string; // In lovelace
  
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'expired';
  
  createdAt: number;
  expiresAt: number;
  completedAt?: number;
}

export interface Subscription {
  subscriptionId: string;
  dappId: string;
  
  tier: string;
  amount: number;
  currency: 'USD' | 'ADA';
  
  interval: 'monthly' | 'yearly';
  status: 'active' | 'paused' | 'cancelled' | 'expired';
  
  currentPeriodStart: number;
  currentPeriodEnd: number;
  
  nextBillingDate?: number;
  cancelAt?: number;
  
  createdAt: number;
  updatedAt: number;
}

/**
 * Payment Processor
 */
export class PaymentProcessor {
  private config: Required<PaymentProcessorConfig>;
  private paymentIntents: Map<string, PaymentIntent>;
  private transactions: Map<string, PaymentTransaction>;
  private subscriptions: Map<string, Subscription>;

  constructor(config: PaymentProcessorConfig = {}) {
    this.config = {
      cardanoEnabled: config.cardanoEnabled ?? true,
      cardanoPaymentAddress: config.cardanoPaymentAddress || '',
      cardanoNetwork: config.cardanoNetwork || 'mainnet',
      
      fiatEnabled: config.fiatEnabled ?? false,
      stripeApiKey: config.stripeApiKey || '',
      
      webhookUrl: config.webhookUrl || '',
      webhookSecret: config.webhookSecret || crypto.randomBytes(32).toString('hex'),
      
      minCardanoConfirmations: config.minCardanoConfirmations ?? 3,
      adaUsdRate: config.adaUsdRate ?? 0.5, // Default rate, should be updated
    };

    this.paymentIntents = new Map();
    this.transactions = new Map();
    this.subscriptions = new Map();
  }

  /**
   * Create a payment intent
   */
  async createPaymentIntent(params: {
    dappId?: string;
    advertiserId?: string;
    amount: number;
    currency: 'USD' | 'ADA';
    description?: string;
    paymentMethod?: 'cardano' | 'stripe';
  }): Promise<PaymentIntent> {
    const intentId = this.generatePaymentIntentId();
    const now = Date.now();
    const expiresIn = 24 * 60 * 60 * 1000; // 24 hours

    let cardanoPaymentAddress: string | undefined;
    let expectedAmount: string | undefined;

    // For Cardano payments
    if (params.paymentMethod === 'cardano' && this.config.cardanoEnabled) {
      cardanoPaymentAddress = this.config.cardanoPaymentAddress;
      
      // Convert USD to ADA if needed
      const adaAmount = params.currency === 'USD'
        ? params.amount / this.config.adaUsdRate
        : params.amount;
      
      expectedAmount = Math.floor(adaAmount * 1_000_000).toString(); // Convert to lovelace
    }

    const intent: PaymentIntent = {
      intentId,
      dappId: params.dappId,
      advertiserId: params.advertiserId,
      amount: params.amount,
      currency: params.currency,
      description: params.description,
      cardanoPaymentAddress,
      expectedAmount,
      status: 'pending',
      createdAt: now,
      expiresAt: now + expiresIn,
    };

    this.paymentIntents.set(intentId, intent);
    return intent;
  }

  /**
   * Verify Cardano payment
   */
  async verifyCardanoPayment(params: {
    intentId: string;
    txHash: string;
    amount: string; // In lovelace
    confirmations: number;
  }): Promise<PaymentTransaction | null> {
    const intent = this.paymentIntents.get(params.intentId);
    if (!intent) return null;

    // Check if payment matches expected amount
    if (intent.expectedAmount && params.amount !== intent.expectedAmount) {
      console.warn(`Amount mismatch: expected ${intent.expectedAmount}, got ${params.amount}`);
      return null;
    }

    // Check confirmations
    const isConfirmed = params.confirmations >= this.config.minCardanoConfirmations;
    const status = isConfirmed ? 'confirmed' : 'pending';

    const transaction: PaymentTransaction = {
      txId: this.generateTransactionId(),
      dappId: intent.dappId,
      advertiserId: intent.advertiserId,
      amount: intent.amount,
      currency: intent.currency,
      cardanoTxHash: params.txHash,
      cardanoAddress: intent.cardanoPaymentAddress,
      status,
      confirmations: params.confirmations,
      timestamp: Date.now(),
      confirmedAt: isConfirmed ? Date.now() : undefined,
    };

    this.transactions.set(transaction.txId, transaction);

    // Update intent status
    if (isConfirmed) {
      intent.status = 'completed';
      intent.completedAt = Date.now();
      this.paymentIntents.set(params.intentId, intent);
    }

    return transaction;
  }

  /**
   * Create subscription
   */
  async createSubscription(params: {
    dappId: string;
    tier: string;
    amount: number;
    currency: 'USD' | 'ADA';
    interval?: 'monthly' | 'yearly';
  }): Promise<Subscription> {
    const subscriptionId = this.generateSubscriptionId();
    const now = Date.now();
    const interval = params.interval || 'monthly';
    
    const periodDuration = interval === 'monthly'
      ? 30 * 24 * 60 * 60 * 1000
      : 365 * 24 * 60 * 60 * 1000;

    const subscription: Subscription = {
      subscriptionId,
      dappId: params.dappId,
      tier: params.tier,
      amount: params.amount,
      currency: params.currency,
      interval,
      status: 'active',
      currentPeriodStart: now,
      currentPeriodEnd: now + periodDuration,
      nextBillingDate: now + periodDuration,
      createdAt: now,
      updatedAt: now,
    };

    this.subscriptions.set(subscriptionId, subscription);
    return subscription;
  }

  /**
   * Renew subscription (process recurring payment)
   */
  async renewSubscription(subscriptionId: string): Promise<PaymentIntent | null> {
    const subscription = this.subscriptions.get(subscriptionId);
    if (!subscription || subscription.status !== 'active') {
      return null;
    }

    const now = Date.now();
    
    // Check if it's time to renew
    if (subscription.nextBillingDate && now < subscription.nextBillingDate) {
      return null; // Not yet time to renew
    }

    // Create payment intent for renewal
    const intent = await this.createPaymentIntent({
      dappId: subscription.dappId,
      amount: subscription.amount,
      currency: subscription.currency,
      description: `Subscription renewal - ${subscription.tier}`,
      paymentMethod: 'cardano',
    });

    return intent;
  }

  /**
   * Cancel subscription
   */
  async cancelSubscription(
    subscriptionId: string,
    cancelImmediately: boolean = false
  ): Promise<Subscription | null> {
    const subscription = this.subscriptions.get(subscriptionId);
    if (!subscription) return null;

    const now = Date.now();

    if (cancelImmediately) {
      subscription.status = 'cancelled';
      subscription.cancelAt = now;
    } else {
      // Cancel at end of current period
      subscription.cancelAt = subscription.currentPeriodEnd;
      subscription.nextBillingDate = undefined;
    }

    subscription.updatedAt = now;
    this.subscriptions.set(subscriptionId, subscription);

    return subscription;
  }

  /**
   * Get payment transaction
   */
  getTransaction(txId: string): PaymentTransaction | undefined {
    return this.transactions.get(txId);
  }

  /**
   * Get all transactions for a dApp
   */
  getDAppTransactions(dappId: string): PaymentTransaction[] {
    return Array.from(this.transactions.values())
      .filter(tx => tx.dappId === dappId);
  }

  /**
   * Get subscription
   */
  getSubscription(subscriptionId: string): Subscription | undefined {
    return this.subscriptions.get(subscriptionId);
  }

  /**
   * Get subscription by dApp ID
   */
  getDAppSubscription(dappId: string): Subscription | undefined {
    return Array.from(this.subscriptions.values())
      .find(sub => sub.dappId === dappId && sub.status === 'active');
  }

  /**
   * Update ADA/USD exchange rate
   */
  updateExchangeRate(adaUsdRate: number): void {
    this.config.adaUsdRate = adaUsdRate;
  }

  /**
   * Convert USD to ADA
   */
  convertUsdToAda(usdAmount: number): number {
    return usdAmount / this.config.adaUsdRate;
  }

  /**
   * Convert ADA to USD
   */
  convertAdaToUsd(adaAmount: number): number {
    return adaAmount * this.config.adaUsdRate;
  }

  /**
   * Generate webhook signature for payment notifications
   */
  generateWebhookSignature(payload: string): string {
    return crypto
      .createHmac('sha256', this.config.webhookSecret)
      .update(payload)
      .digest('hex');
  }

  /**
   * Verify webhook signature
   */
  verifyWebhookSignature(payload: string, signature: string): boolean {
    const expectedSignature = this.generateWebhookSignature(payload);
    return crypto.timingSafeEqual(
      Buffer.from(signature),
      Buffer.from(expectedSignature)
    );
  }

  /**
   * Generate payment intent ID
   */
  private generatePaymentIntentId(): string {
    return `pi_${crypto.randomBytes(16).toString('hex')}`;
  }

  /**
   * Generate transaction ID
   */
  private generateTransactionId(): string {
    return `tx_${crypto.randomBytes(16).toString('hex')}`;
  }

  /**
   * Generate subscription ID
   */
  private generateSubscriptionId(): string {
    return `sub_${crypto.randomBytes(16).toString('hex')}`;
  }

  /**
   * Expire old payment intents
   */
  async expireOldIntents(): Promise<string[]> {
    const now = Date.now();
    const expiredIds: string[] = [];

    for (const [intentId, intent] of this.paymentIntents.entries()) {
      if (intent.status === 'pending' && now > intent.expiresAt) {
        intent.status = 'expired';
        this.paymentIntents.set(intentId, intent);
        expiredIds.push(intentId);
      }
    }

    return expiredIds;
  }

  /**
   * Get revenue analytics
   */
  getRevenueAnalytics(params?: {
    startDate?: number;
    endDate?: number;
    currency?: 'USD' | 'ADA';
  }): {
    totalRevenue: number;
    transactionCount: number;
    averageTransaction: number;
    activeSubscriptions: number;
    monthlyRecurringRevenue: number;
  } {
    const transactions = Array.from(this.transactions.values()).filter(tx => {
      if (tx.status !== 'confirmed') return false;
      if (params?.startDate && tx.timestamp < params.startDate) return false;
      if (params?.endDate && tx.timestamp > params.endDate) return false;
      if (params?.currency && tx.currency !== params.currency) return false;
      return true;
    });

    const totalRevenue = transactions.reduce((sum, tx) => sum + tx.amount, 0);
    const transactionCount = transactions.length;
    const averageTransaction = transactionCount > 0 ? totalRevenue / transactionCount : 0;

    const activeSubscriptions = Array.from(this.subscriptions.values())
      .filter(sub => sub.status === 'active').length;

    const monthlyRecurringRevenue = Array.from(this.subscriptions.values())
      .filter(sub => sub.status === 'active')
      .reduce((sum, sub) => {
        const monthlyAmount = sub.interval === 'yearly' ? sub.amount / 12 : sub.amount;
        return sum + (params?.currency && sub.currency !== params.currency ? 0 : monthlyAmount);
      }, 0);

    return {
      totalRevenue,
      transactionCount,
      averageTransaction,
      activeSubscriptions,
      monthlyRecurringRevenue,
    };
  }
}

export default PaymentProcessor;
