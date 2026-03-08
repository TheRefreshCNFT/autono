/**
 * Payment Processor
 * Handles payment processing for dApp integrations and advertisements
 * Supports both Cardano native payments and traditional fiat
 */
import { PaymentTransaction } from './types';
export interface PaymentProcessorConfig {
    cardanoEnabled?: boolean;
    cardanoPaymentAddress?: string;
    cardanoNetwork?: 'mainnet' | 'testnet';
    fiatEnabled?: boolean;
    stripeApiKey?: string;
    webhookUrl?: string;
    webhookSecret?: string;
    minCardanoConfirmations?: number;
    adaUsdRate?: number;
}
export interface PaymentIntent {
    intentId: string;
    dappId?: string;
    advertiserId?: string;
    amount: number;
    currency: 'USD' | 'ADA';
    description?: string;
    cardanoPaymentAddress?: string;
    expectedAmount?: string;
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
export declare class PaymentProcessor {
    private config;
    private paymentIntents;
    private transactions;
    private subscriptions;
    constructor(config?: PaymentProcessorConfig);
    /**
     * Create a payment intent
     */
    createPaymentIntent(params: {
        dappId?: string;
        advertiserId?: string;
        amount: number;
        currency: 'USD' | 'ADA';
        description?: string;
        paymentMethod?: 'cardano' | 'stripe';
    }): Promise<PaymentIntent>;
    /**
     * Verify Cardano payment
     */
    verifyCardanoPayment(params: {
        intentId: string;
        txHash: string;
        amount: string;
        confirmations: number;
    }): Promise<PaymentTransaction | null>;
    /**
     * Create subscription
     */
    createSubscription(params: {
        dappId: string;
        tier: string;
        amount: number;
        currency: 'USD' | 'ADA';
        interval?: 'monthly' | 'yearly';
    }): Promise<Subscription>;
    /**
     * Renew subscription (process recurring payment)
     */
    renewSubscription(subscriptionId: string): Promise<PaymentIntent | null>;
    /**
     * Cancel subscription
     */
    cancelSubscription(subscriptionId: string, cancelImmediately?: boolean): Promise<Subscription | null>;
    /**
     * Get payment transaction
     */
    getTransaction(txId: string): PaymentTransaction | undefined;
    /**
     * Get all transactions for a dApp
     */
    getDAppTransactions(dappId: string): PaymentTransaction[];
    /**
     * Get subscription
     */
    getSubscription(subscriptionId: string): Subscription | undefined;
    /**
     * Get subscription by dApp ID
     */
    getDAppSubscription(dappId: string): Subscription | undefined;
    /**
     * Update ADA/USD exchange rate
     */
    updateExchangeRate(adaUsdRate: number): void;
    /**
     * Convert USD to ADA
     */
    convertUsdToAda(usdAmount: number): number;
    /**
     * Convert ADA to USD
     */
    convertAdaToUsd(adaAmount: number): number;
    /**
     * Generate webhook signature for payment notifications
     */
    generateWebhookSignature(payload: string): string;
    /**
     * Verify webhook signature
     */
    verifyWebhookSignature(payload: string, signature: string): boolean;
    /**
     * Generate payment intent ID
     */
    private generatePaymentIntentId;
    /**
     * Generate transaction ID
     */
    private generateTransactionId;
    /**
     * Generate subscription ID
     */
    private generateSubscriptionId;
    /**
     * Expire old payment intents
     */
    expireOldIntents(): Promise<string[]>;
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
    };
}
export default PaymentProcessor;
