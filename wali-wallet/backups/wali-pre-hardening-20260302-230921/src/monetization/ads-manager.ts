/**
 * Advertisement Manager
 * Handles ad placement, targeting, and performance tracking
 */

import crypto from 'crypto';
import {
  Advertisement,
  AdType,
  AdPlacement,
  AdStatus,
  AdContent,
  AdTargeting,
  AdImpression,
  AdClick,
} from './types';

export interface AdsManagerConfig {
  // Privacy settings
  respectDoNotTrack?: boolean;
  requireUserConsent?: boolean;
  
  // Frequency limits
  maxAdsPerSession?: number;
  maxAdsPerDay?: number;
  
  // Performance
  cacheEnabled?: boolean;
  cacheTTL?: number;
}

/**
 * Ad Context - information about current user/session for targeting
 */
export interface AdContext {
  sessionId: string;
  userId?: string;
  
  // Privacy settings
  userConsented: boolean;
  doNotTrack: boolean;
  
  // Contextual information
  currentAction?: 'transaction' | 'balance-check' | 'nft-browse' | 'defi';
  placement: AdPlacement;
  
  // Optional targeting info (only if user consented)
  country?: string;
  region?: string;
  interests?: string[];
}

/**
 * Advertisement Manager
 */
export class AdsManager {
  private config: Required<AdsManagerConfig>;
  private advertisements: Map<string, Advertisement>;
  private impressions: Map<string, AdImpression[]>; // sessionId -> impressions
  private clicks: Map<string, AdClick[]>; // sessionId -> clicks
  private dailyImpressions: Map<string, number>; // userId -> count
  private dailyImpressionsDate: Map<string, string>; // userId -> date

  constructor(config: AdsManagerConfig = {}) {
    this.config = {
      respectDoNotTrack: config.respectDoNotTrack ?? true,
      requireUserConsent: config.requireUserConsent ?? true,
      maxAdsPerSession: config.maxAdsPerSession ?? 5,
      maxAdsPerDay: config.maxAdsPerDay ?? 20,
      cacheEnabled: config.cacheEnabled ?? true,
      cacheTTL: config.cacheTTL ?? 300000, // 5 minutes
    };

    this.advertisements = new Map();
    this.impressions = new Map();
    this.clicks = new Map();
    this.dailyImpressions = new Map();
    this.dailyImpressionsDate = new Map();
  }

  /**
   * Create a new advertisement
   */
  async createAd(params: {
    advertiserId: string;
    type: AdType;
    placement: AdPlacement;
    content: AdContent;
    targeting?: AdTargeting;
    payment: {
      model: 'cpm' | 'cpc' | 'flat';
      rateCpm?: number;
      rateCpc?: number;
      flatRate?: number;
      budget?: number;
    };
    startDate?: number;
    endDate?: number;
  }): Promise<Advertisement> {
    const adId = this.generateAdId();
    const now = Date.now();

    const ad: Advertisement = {
      adId,
      advertiserId: params.advertiserId,
      type: params.type,
      placement: params.placement,
      status: 'active',
      content: params.content,
      targeting: params.targeting,
      payment: {
        model: params.payment.model,
        rateCpm: params.payment.rateCpm,
        rateCpc: params.payment.rateCpc,
        flatRate: params.payment.flatRate,
        totalSpent: 0,
        budget: params.payment.budget,
      },
      impressions: 0,
      clicks: 0,
      conversions: 0,
      createdAt: now,
      updatedAt: now,
      startDate: params.startDate,
      endDate: params.endDate,
    };

    this.advertisements.set(adId, ad);
    return ad;
  }

  /**
   * Get advertisement to display based on context
   */
  async getAdForContext(context: AdContext): Promise<Advertisement | null> {
    // Privacy checks
    if (this.config.respectDoNotTrack && context.doNotTrack) {
      return null; // Respect Do Not Track
    }

    if (this.config.requireUserConsent && !context.userConsented) {
      return null; // User hasn't consented
    }

    // Frequency limits
    if (!this.checkFrequencyLimits(context)) {
      return null; // Frequency limit exceeded
    }

    // Get eligible ads for this placement
    const eligibleAds = this.getEligibleAds(context);
    
    if (eligibleAds.length === 0) {
      return null;
    }

    // Select ad (simple random selection, can be improved with bidding/prioritization)
    const selectedAd = eligibleAds[Math.floor(Math.random() * eligibleAds.length)];

    return selectedAd;
  }

  /**
   * Record an ad impression
   */
  async recordImpression(params: {
    adId: string;
    context: AdContext;
  }): Promise<void> {
    const ad = this.advertisements.get(params.adId);
    if (!ad) throw new Error(`Ad not found: ${params.adId}`);

    const impression: AdImpression = {
      adId: params.adId,
      userId: params.context.userId,
      sessionId: params.context.sessionId,
      timestamp: Date.now(),
      placement: params.context.placement,
      context: params.context.currentAction,
      userConsented: params.context.userConsented,
      doNotTrack: params.context.doNotTrack,
    };

    // Store impression
    const sessionImpressions = this.impressions.get(params.context.sessionId) || [];
    sessionImpressions.push(impression);
    this.impressions.set(params.context.sessionId, sessionImpressions);

    // Update ad stats
    ad.impressions++;
    ad.updatedAt = Date.now();

    // Update daily count
    if (params.context.userId) {
      this.updateDailyImpressions(params.context.userId);
    }

    // Calculate cost (CPM model)
    if (ad.payment.model === 'cpm' && ad.payment.rateCpm) {
      const cost = ad.payment.rateCpm / 1000; // Cost per impression
      ad.payment.totalSpent += cost;
    }

    this.advertisements.set(params.adId, ad);
  }

  /**
   * Record an ad click
   */
  async recordClick(params: {
    adId: string;
    context: AdContext;
  }): Promise<void> {
    const ad = this.advertisements.get(params.adId);
    if (!ad) throw new Error(`Ad not found: ${params.adId}`);

    const click: AdClick = {
      adId: params.adId,
      userId: params.context.userId,
      sessionId: params.context.sessionId,
      timestamp: Date.now(),
      targetUrl: ad.content.targetUrl,
      userConsented: params.context.userConsented,
    };

    // Store click
    const sessionClicks = this.clicks.get(params.context.sessionId) || [];
    sessionClicks.push(click);
    this.clicks.set(params.context.sessionId, sessionClicks);

    // Update ad stats
    ad.clicks++;
    ad.updatedAt = Date.now();

    // Calculate cost (CPC model)
    if (ad.payment.model === 'cpc' && ad.payment.rateCpc) {
      ad.payment.totalSpent += ad.payment.rateCpc;
    }

    this.advertisements.set(params.adId, ad);
  }

  /**
   * Get ad performance metrics
   */
  getAdPerformance(adId: string): {
    impressions: number;
    clicks: number;
    ctr: number; // Click-through rate
    conversions: number;
    conversionRate: number;
    totalSpent: number;
    avgCostPerClick?: number;
    avgCostPerConversion?: number;
  } | undefined {
    const ad = this.advertisements.get(adId);
    if (!ad) return undefined;

    const ctr = ad.impressions > 0 ? (ad.clicks / ad.impressions) * 100 : 0;
    const conversionRate = ad.clicks > 0 ? (ad.conversions / ad.clicks) * 100 : 0;
    const avgCostPerClick = ad.clicks > 0 ? ad.payment.totalSpent / ad.clicks : undefined;
    const avgCostPerConversion = ad.conversions > 0 ? ad.payment.totalSpent / ad.conversions : undefined;

    return {
      impressions: ad.impressions,
      clicks: ad.clicks,
      ctr,
      conversions: ad.conversions,
      conversionRate,
      totalSpent: ad.payment.totalSpent,
      avgCostPerClick,
      avgCostPerConversion,
    };
  }

  /**
   * Pause or activate an advertisement
   */
  async setAdStatus(adId: string, status: AdStatus): Promise<Advertisement | undefined> {
    const ad = this.advertisements.get(adId);
    if (!ad) return undefined;

    ad.status = status;
    ad.updatedAt = Date.now();
    this.advertisements.set(adId, ad);

    return ad;
  }

  /**
   * Get eligible ads for context
   */
  private getEligibleAds(context: AdContext): Advertisement[] {
    const now = Date.now();

    return Array.from(this.advertisements.values()).filter(ad => {
      // Must be active
      if (ad.status !== 'active') return false;

      // Must match placement
      if (ad.placement !== context.placement) return false;

      // Check date range
      if (ad.startDate && now < ad.startDate) return false;
      if (ad.endDate && now > ad.endDate) return false;

      // Check budget
      if (ad.payment.budget && ad.payment.totalSpent >= ad.payment.budget) return false;

      // Check targeting (if user consented)
      if (ad.targeting && context.userConsented) {
        if (!this.matchesTargeting(ad.targeting, context)) {
          return false;
        }
      }

      return true;
    });
  }

  /**
   * Check if context matches ad targeting
   */
  private matchesTargeting(targeting: AdTargeting, context: AdContext): boolean {
    // Country/region targeting
    if (targeting.countries && context.country) {
      if (!targeting.countries.includes(context.country)) return false;
    }

    if (targeting.regions && context.region) {
      if (!targeting.regions.includes(context.region)) return false;
    }

    // Context targeting
    if (targeting.contexts && context.currentAction) {
      if (!targeting.contexts.includes(context.currentAction)) return false;
    }

    // Interest targeting (opt-in only)
    if (targeting.interests && context.interests) {
      const hasMatchingInterest = targeting.interests.some(interest =>
        context.interests?.includes(interest)
      );
      if (!hasMatchingInterest) return false;
    }

    return true;
  }

  /**
   * Check frequency limits
   */
  private checkFrequencyLimits(context: AdContext): boolean {
    // Session limit
    const sessionImpressions = this.impressions.get(context.sessionId)?.length || 0;
    if (sessionImpressions >= this.config.maxAdsPerSession) {
      return false;
    }

    // Daily limit (if userId available)
    if (context.userId) {
      const dailyCount = this.getDailyImpressions(context.userId);
      if (dailyCount >= this.config.maxAdsPerDay) {
        return false;
      }
    }

    return true;
  }

  /**
   * Get daily impression count for user
   */
  private getDailyImpressions(userId: string): number {
    const today = new Date().toISOString().split('T')[0];
    const lastDate = this.dailyImpressionsDate.get(userId);

    if (lastDate !== today) {
      // Reset count for new day
      this.dailyImpressions.set(userId, 0);
      this.dailyImpressionsDate.set(userId, today);
      return 0;
    }

    return this.dailyImpressions.get(userId) || 0;
  }

  /**
   * Update daily impression count
   */
  private updateDailyImpressions(userId: string): void {
    const today = new Date().toISOString().split('T')[0];
    const lastDate = this.dailyImpressionsDate.get(userId);

    if (lastDate !== today) {
      this.dailyImpressions.set(userId, 1);
      this.dailyImpressionsDate.set(userId, today);
    } else {
      const current = this.dailyImpressions.get(userId) || 0;
      this.dailyImpressions.set(userId, current + 1);
    }
  }

  /**
   * Generate unique ad ID
   */
  private generateAdId(): string {
    return `ad_${crypto.randomBytes(16).toString('hex')}`;
  }

  /**
   * List all advertisements (with optional filters)
   */
  listAds(filter?: {
    advertiserId?: string;
    placement?: AdPlacement;
    status?: AdStatus;
  }): Advertisement[] {
    let ads = Array.from(this.advertisements.values());

    if (filter?.advertiserId) {
      ads = ads.filter(ad => ad.advertiserId === filter.advertiserId);
    }

    if (filter?.placement) {
      ads = ads.filter(ad => ad.placement === filter.placement);
    }

    if (filter?.status) {
      ads = ads.filter(ad => ad.status === filter.status);
    }

    return ads;
  }
}

export default AdsManager;
