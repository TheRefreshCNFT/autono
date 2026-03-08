/**
 * dApp Registry System
 * Manages dApp integrations, payments, and feature gating
 */

import crypto from 'crypto';
import {
  DAppIntegration,
  DAppTier,
  PaymentStatus,
  TierDefinition,
  DEFAULT_TIERS,
  PaymentTransaction,
} from './types';

export interface DAppRegistryConfig {
  storageBackend?: 'memory' | 'file' | 'database';
  storagePath?: string;
  
  // Trial period (days)
  trialDurationDays?: number;
  
  // Grace period for expired payments (days)
  gracePeriodDays?: number;
}

/**
 * dApp Registry - manages integration lifecycle
 */
export class DAppRegistry {
  private config: Required<DAppRegistryConfig>;
  private integrations: Map<string, DAppIntegration>;
  private apiKeys: Map<string, string>; // apiKey -> dappId
  private tiers: Map<DAppTier, TierDefinition>;

  constructor(config: DAppRegistryConfig = {}) {
    this.config = {
      storageBackend: config.storageBackend || 'memory',
      storagePath: config.storagePath || './data/dapp-registry.json',
      trialDurationDays: config.trialDurationDays || 14,
      gracePeriodDays: config.gracePeriodDays || 7,
    };

    this.integrations = new Map();
    this.apiKeys = new Map();
    this.tiers = new Map(DEFAULT_TIERS.map(tier => [tier.tier, tier]));

    // Load existing integrations if available
    this.loadIntegrations();
  }

  /**
   * Register a new dApp integration
   */
  async registerDApp(params: {
    name: string;
    description?: string;
    website?: string;
    contactEmail?: string;
    tier?: DAppTier;
    cardanoPaymentAddress?: string;
  }): Promise<DAppIntegration> {
    const dappId = this.generateDAppId(params.name);
    const apiKey = this.generateApiKey();
    const now = Date.now();

    const tier = params.tier || 'basic';
    const tierDef = this.tiers.get(tier)!;

    const integration: DAppIntegration = {
      dappId,
      name: params.name,
      description: params.description,
      website: params.website,
      contactEmail: params.contactEmail,
      
      paymentStatus: 'trial',
      tier,
      
      features: tierDef.features,
      monthlyFee: tierDef.monthlyPrice,
      
      connectedUsers: 0,
      maxUsers: tierDef.maxUsers,
      
      apiKey,
      cardanoPaymentAddress: params.cardanoPaymentAddress,
      
      createdAt: now,
      updatedAt: now,
      expiresAt: now + (this.config.trialDurationDays * 24 * 60 * 60 * 1000),
    };

    this.integrations.set(dappId, integration);
    this.apiKeys.set(apiKey, dappId);
    
    await this.saveIntegrations();
    
    return integration;
  }

  /**
   * Get dApp integration by ID
   */
  getDApp(dappId: string): DAppIntegration | undefined {
    return this.integrations.get(dappId);
  }

  /**
   * Get dApp integration by API key
   */
  getDAppByApiKey(apiKey: string): DAppIntegration | undefined {
    const dappId = this.apiKeys.get(apiKey);
    return dappId ? this.integrations.get(dappId) : undefined;
  }

  /**
   * List all dApp integrations (with optional filters)
   */
  listDApps(filter?: {
    tier?: DAppTier;
    paymentStatus?: PaymentStatus;
  }): DAppIntegration[] {
    let apps = Array.from(this.integrations.values());

    if (filter?.tier) {
      apps = apps.filter(app => app.tier === filter.tier);
    }

    if (filter?.paymentStatus) {
      apps = apps.filter(app => app.paymentStatus === filter.paymentStatus);
    }

    return apps;
  }

  /**
   * Update dApp integration
   */
  async updateDApp(
    dappId: string,
    updates: Partial<DAppIntegration>
  ): Promise<DAppIntegration | undefined> {
    const integration = this.integrations.get(dappId);
    if (!integration) return undefined;

    const updated: DAppIntegration = {
      ...integration,
      ...updates,
      dappId, // Immutable
      createdAt: integration.createdAt, // Immutable
      updatedAt: Date.now(),
    };

    this.integrations.set(dappId, updated);
    await this.saveIntegrations();

    return updated;
  }

  /**
   * Upgrade dApp tier
   */
  async upgradeTier(dappId: string, newTier: DAppTier): Promise<DAppIntegration | undefined> {
    const integration = this.integrations.get(dappId);
    if (!integration) return undefined;

    const tierDef = this.tiers.get(newTier);
    if (!tierDef) throw new Error(`Invalid tier: ${newTier}`);

    return this.updateDApp(dappId, {
      tier: newTier,
      features: tierDef.features,
      monthlyFee: tierDef.monthlyPrice,
      maxUsers: tierDef.maxUsers,
    });
  }

  /**
   * Process payment for dApp
   */
  async processPayment(params: {
    dappId: string;
    transaction: PaymentTransaction;
  }): Promise<DAppIntegration | undefined> {
    const integration = this.integrations.get(params.dappId);
    if (!integration) return undefined;

    const now = Date.now();
    const monthMs = 30 * 24 * 60 * 60 * 1000;

    return this.updateDApp(params.dappId, {
      paymentStatus: 'paid',
      lastPaymentTxHash: params.transaction.cardanoTxHash,
      expiresAt: now + monthMs,
    });
  }

  /**
   * Check if dApp has access to a feature
   */
  hasFeature(dappId: string, feature: string): boolean {
    const integration = this.integrations.get(dappId);
    if (!integration) return false;

    // Check payment status
    if (integration.paymentStatus === 'expired') {
      const gracePeriodMs = this.config.gracePeriodDays * 24 * 60 * 60 * 1000;
      const now = Date.now();
      
      if (integration.expiresAt && now > integration.expiresAt + gracePeriodMs) {
        return false; // Grace period expired
      }
    }

    return integration.features.includes(feature);
  }

  /**
   * Check if dApp is within user limits
   */
  withinUserLimits(dappId: string): boolean {
    const integration = this.integrations.get(dappId);
    if (!integration) return false;

    // Unlimited users (enterprise)
    if (integration.maxUsers === -1) return true;

    return integration.connectedUsers < integration.maxUsers;
  }

  /**
   * Increment connected user count
   */
  async incrementUsers(dappId: string): Promise<boolean> {
    const integration = this.integrations.get(dappId);
    if (!integration) return false;

    if (!this.withinUserLimits(dappId)) {
      return false; // User limit reached
    }

    await this.updateDApp(dappId, {
      connectedUsers: integration.connectedUsers + 1,
    });

    return true;
  }

  /**
   * Get usage analytics for a dApp
   */
  getAnalytics(dappId: string): {
    connectedUsers: number;
    maxUsers: number;
    utilizationPercent: number;
    tier: DAppTier;
    paymentStatus: PaymentStatus;
    daysUntilExpiration?: number;
  } | undefined {
    const integration = this.integrations.get(dappId);
    if (!integration) return undefined;

    const utilizationPercent = integration.maxUsers === -1
      ? 0 // Unlimited
      : (integration.connectedUsers / integration.maxUsers) * 100;

    const daysUntilExpiration = integration.expiresAt
      ? Math.max(0, Math.floor((integration.expiresAt - Date.now()) / (24 * 60 * 60 * 1000)))
      : undefined;

    return {
      connectedUsers: integration.connectedUsers,
      maxUsers: integration.maxUsers,
      utilizationPercent,
      tier: integration.tier,
      paymentStatus: integration.paymentStatus,
      daysUntilExpiration,
    };
  }

  /**
   * Expire integrations with overdue payments
   */
  async expireOverdueIntegrations(): Promise<string[]> {
    const now = Date.now();
    const expiredIds: string[] = [];

    for (const [dappId, integration] of this.integrations.entries()) {
      if (
        integration.paymentStatus === 'paid' &&
        integration.expiresAt &&
        now > integration.expiresAt
      ) {
        await this.updateDApp(dappId, {
          paymentStatus: 'expired',
        });
        expiredIds.push(dappId);
      }
    }

    return expiredIds;
  }

  /**
   * Generate unique dApp ID
   */
  private generateDAppId(name: string): string {
    const timestamp = Date.now().toString(36);
    const random = crypto.randomBytes(4).toString('hex');
    const nameSlug = name.toLowerCase().replace(/[^a-z0-9]/g, '-').substring(0, 20);
    return `dapp_${nameSlug}_${timestamp}_${random}`;
  }

  /**
   * Generate API key
   */
  private generateApiKey(): string {
    return `wali_${crypto.randomBytes(32).toString('base64url')}`;
  }

  /**
   * Load integrations from storage
   */
  private async loadIntegrations(): Promise<void> {
    // TODO: Implement file/database loading based on storageBackend
    // For now, using in-memory storage
  }

  /**
   * Save integrations to storage
   */
  private async saveIntegrations(): Promise<void> {
    // TODO: Implement file/database saving based on storageBackend
    // For now, using in-memory storage
  }

  /**
   * Get tier definition
   */
  getTierDefinition(tier: DAppTier): TierDefinition | undefined {
    return this.tiers.get(tier);
  }

  /**
   * Get all tier definitions
   */
  getAllTiers(): TierDefinition[] {
    return Array.from(this.tiers.values());
  }
}

export default DAppRegistry;
