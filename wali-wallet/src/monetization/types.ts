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
  
  // Payment & Status
  paymentStatus: PaymentStatus;
  tier: DAppTier;
  
  // Features enabled for this tier
  features: string[];
  
  // Pricing
  monthlyFee: number; // In USD (or ADA equivalent)
  
  // Usage tracking
  connectedUsers: number;
  maxUsers: number;
  
  // API credentials
  apiKey?: string;
  webhookUrl?: string;
  
  // Metadata
  createdAt: number;
  updatedAt: number;
  expiresAt?: number;
  
  // Cardano payment details (optional - native payments!)
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
  
  // For native/sponsored ads
  sponsorName?: string;
  sponsorLogo?: string;
}

/**
 * Advertisement Targeting (privacy-first, opt-in only)
 */
export interface AdTargeting {
  // Location-based (country/region only, no precise location)
  countries?: string[];
  regions?: string[];
  
  // User preferences (opt-in only)
  interests?: string[];
  
  // Contextual (based on what user is doing)
  contexts?: ('transaction' | 'balance-check' | 'nft-browse' | 'defi')[];
  
  // Time-based
  startTime?: number;
  endTime?: number;
  
  // Frequency
  maxImpressionsPerUser?: number;
  maxImpressionsPerDay?: number;
}

/**
 * Advertisement Payment Information
 */
export interface AdPayment {
  // Pricing model
  model: 'cpm' | 'cpc' | 'flat'; // Cost per mille, cost per click, or flat rate
  
  // Rates (in USD or ADA)
  rateCpm?: number;
  rateCpc?: number;
  flatRate?: number;
  
  // Payment tracking
  totalSpent: number;
  budget?: number;
  
  // Cardano payment details
  paymentAddress?: string;
  paymentTxHash?: string;
}

/**
 * Advertisement Record
 */
export interface Advertisement {
  adId: string;
  advertiserId: string;
  
  // Ad configuration
  type: AdType;
  placement: AdPlacement;
  status: AdStatus;
  
  // Content & targeting
  content: AdContent;
  targeting?: AdTargeting;
  
  // Payment & performance
  payment: AdPayment;
  
  // Analytics
  impressions: number;
  clicks: number;
  conversions: number;
  
  // Metadata
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
  userId?: string; // Optional - only if user consents
  sessionId: string;
  timestamp: number;
  placement: AdPlacement;
  context?: string;
  
  // Privacy-friendly metadata
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
  
  // Analytics
  userConsented: boolean;
}

/**
 * Monetization Configuration
 */
export interface MonetizationConfig {
  // dApp integrations
  dappIntegrations: {
    enabled: boolean;
    registryEndpoint?: string;
    requireApiKey?: boolean;
  };
  
  // Advertisements
  advertisements: {
    enabled: boolean;
    maxPerSession?: number;
    maxPerDay?: number;
    respectDoNotTrack?: boolean;
    
    // Privacy settings
    requireUserConsent?: boolean;
    allowTargeting?: boolean;
  };
  
  // Payment processing
  payments: {
    acceptCardano?: boolean;
    acceptFiat?: boolean;
    cardanoPaymentAddress?: string;
    
    // Webhook for payment notifications
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
export const DEFAULT_TIERS: TierDefinition[] = [
  {
    tier: 'basic',
    name: 'Basic',
    monthlyPrice: 99,
    maxUsers: 1000,
    features: [
      'Standard API access',
      'Basic analytics',
      'Community support',
      '99.5% uptime SLA',
    ],
    support: 'community',
  },
  {
    tier: 'premium',
    name: 'Premium',
    monthlyPrice: 299,
    maxUsers: 10000,
    features: [
      'Priority API access',
      'Advanced analytics',
      'Email support',
      'Custom branding',
      'Webhook notifications',
      '99.9% uptime SLA',
    ],
    support: 'email',
  },
  {
    tier: 'enterprise',
    name: 'Enterprise',
    monthlyPrice: 0, // Custom pricing
    maxUsers: -1, // Unlimited
    features: [
      'Dedicated infrastructure',
      'Full analytics suite',
      'Dedicated support',
      'White-label options',
      'Custom integrations',
      'SLA guarantees',
      'On-premise deployment options',
    ],
    support: 'dedicated',
  },
];

/**
 * Payment transaction record
 */
export interface PaymentTransaction {
  txId: string;
  dappId?: string;
  advertiserId?: string;
  
  // Payment details
  amount: number;
  currency: 'USD' | 'ADA';
  
  // Cardano-specific
  cardanoTxHash?: string;
  cardanoAddress?: string;
  
  // Status
  status: 'pending' | 'confirmed' | 'failed';
  confirmations?: number;
  
  // Metadata
  timestamp: number;
  confirmedAt?: number;
  
  // References
  invoiceId?: string;
  receiptUrl?: string;
}

export default {
  DEFAULT_TIERS,
};
