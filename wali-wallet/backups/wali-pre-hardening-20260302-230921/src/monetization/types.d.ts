/**
 * Monetization Type Definitions
 * Supports dApp integrations and advertisement infrastructure
 */
/**
 * dApp Integration Payment Tiers
 */
export type DAppTier = 'basic' | 'premium' | 'enterprise';
export type PaymentStatus = 'trial' | 'paid' | 'expired';
/**
 * dApp Integration Record
 */
export interface DAppIntegration {
    dappId: string;
    name: string;
    description?: string;
    website?: string;
    contactEmail?: string;
    paymentStatus: PaymentStatus;
    tier: DAppTier;
    features: string[];
    monthlyFee: number;
    connectedUsers: number;
    maxUsers: number;
    apiKey?: string;
    webhookUrl?: string;
    createdAt: number;
    updatedAt: number;
    expiresAt?: number;
    cardanoPaymentAddress?: string;
    lastPaymentTxHash?: string;
}
/**
 * Advertisement Types
 */
export type AdType = 'banner' | 'native' | 'sponsored';
export type AdPlacement = 'chat' | 'transaction' | 'dashboard' | 'asset-list';
export type AdStatus = 'active' | 'paused' | 'expired';
/**
 * Advertisement Content
 */
export interface AdContent {
    title: string;
    description: string;
    imageUrl?: string;
    callToAction?: string;
    targetUrl: string;
    sponsorName?: string;
    sponsorLogo?: string;
}
/**
 * Advertisement Targeting (privacy-first, opt-in only)
 */
export interface AdTargeting {
    countries?: string[];
    regions?: string[];
    interests?: string[];
    contexts?: ('transaction' | 'balance-check' | 'nft-browse' | 'defi')[];
    startTime?: number;
    endTime?: number;
    maxImpressionsPerUser?: number;
    maxImpressionsPerDay?: number;
}
/**
 * Advertisement Payment Information
 */
export interface AdPayment {
    model: 'cpm' | 'cpc' | 'flat';
    rateCpm?: number;
    rateCpc?: number;
    flatRate?: number;
    totalSpent: number;
    budget?: number;
    paymentAddress?: string;
    paymentTxHash?: string;
}
/**
 * Advertisement Record
 */
export interface Advertisement {
    adId: string;
    advertiserId: string;
    type: AdType;
    placement: AdPlacement;
    status: AdStatus;
    content: AdContent;
    targeting?: AdTargeting;
    payment: AdPayment;
    impressions: number;
    clicks: number;
    conversions: number;
    createdAt: number;
    updatedAt: number;
    startDate?: number;
    endDate?: number;
}
/**
 * Ad Impression Event (for tracking)
 */
export interface AdImpression {
    adId: string;
    userId?: string;
    sessionId: string;
    timestamp: number;
    placement: AdPlacement;
    context?: string;
    userConsented: boolean;
    doNotTrack: boolean;
}
/**
 * Ad Click Event
 */
export interface AdClick {
    adId: string;
    userId?: string;
    sessionId: string;
    timestamp: number;
    targetUrl: string;
    userConsented: boolean;
}
/**
 * Monetization Configuration
 */
export interface MonetizationConfig {
    dappIntegrations: {
        enabled: boolean;
        registryEndpoint?: string;
        requireApiKey?: boolean;
    };
    advertisements: {
        enabled: boolean;
        maxPerSession?: number;
        maxPerDay?: number;
        respectDoNotTrack?: boolean;
        requireUserConsent?: boolean;
        allowTargeting?: boolean;
    };
    payments: {
        acceptCardano?: boolean;
        acceptFiat?: boolean;
        cardanoPaymentAddress?: string;
        webhookUrl?: string;
        webhookSecret?: string;
    };
}
/**
 * dApp Tier Definitions
 */
export interface TierDefinition {
    tier: DAppTier;
    name: string;
    monthlyPrice: number;
    maxUsers: number;
    features: string[];
    support: 'community' | 'email' | 'priority' | 'dedicated';
}
/**
 * Default tier configurations
 */
export declare const DEFAULT_TIERS: TierDefinition[];
/**
 * Payment transaction record
 */
export interface PaymentTransaction {
    txId: string;
    dappId?: string;
    advertiserId?: string;
    amount: number;
    currency: 'USD' | 'ADA';
    cardanoTxHash?: string;
    cardanoAddress?: string;
    status: 'pending' | 'confirmed' | 'failed';
    confirmations?: number;
    timestamp: number;
    confirmedAt?: number;
    invoiceId?: string;
    receiptUrl?: string;
}
declare const _default: {
    DEFAULT_TIERS: TierDefinition[];
};
export default _default;
