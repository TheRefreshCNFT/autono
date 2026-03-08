# wAli Monetization Module

**Sustainable revenue infrastructure for dApp integrations and advertisements**

## Overview

This module provides a complete monetization infrastructure for wAli, including:

1. **dApp Integration Payments** - Tiered subscription system for dApp developers
2. **Advertisement Management** - Privacy-first ad placement and tracking
3. **Payment Processing** - Cardano-native and fiat payment support

## Architecture

```
monetization/
├── types.ts              # Type definitions for all monetization features
├── dapp-registry.ts      # dApp registration, payment, and feature gating
├── ads-manager.ts        # Ad placement, targeting, and analytics
├── payment-processor.ts  # Payment handling (Cardano + Stripe)
└── index.ts             # Module exports
```

## Quick Start

### Initialize Monetization in wAli

```typescript
import { WaliEngine } from './wali-engine';

const wali = new WaliEngine({
  network: 'mainnet',
  monetization: {
    dappIntegrations: {
      enabled: true,
      registryEndpoint: 'https://api.wali.app/dapps',
    },
    advertisements: {
      enabled: true,
      maxPerSession: 5,
      maxPerDay: 20,
      respectDoNotTrack: true,
      requireUserConsent: true,
    },
    payments: {
      acceptCardano: true,
      cardanoPaymentAddress: 'addr1...',
      webhookUrl: 'https://api.wali.app/webhooks/payment',
    },
  },
});

await wali.initialize();
```

### Register a dApp

```typescript
const registry = wali.getDAppRegistry();

const dapp = await registry.registerDApp({
  name: 'My Awesome dApp',
  description: 'A cool DeFi platform',
  website: 'https://myapp.io',
  contactEmail: 'dev@myapp.io',
  tier: 'basic',
  cardanoPaymentAddress: 'addr1...',
});

console.log('API Key:', dapp.apiKey);
console.log('Trial expires:', new Date(dapp.expiresAt!));
```

### Create an Advertisement

```typescript
const adsManager = wali.getAdsManager();

const ad = await adsManager.createAd({
  advertiserId: 'advertiser-123',
  type: 'native',
  placement: 'chat',
  content: {
    title: 'Stake Your ADA',
    description: 'Earn 5% APY with our verified pool',
    sponsorName: 'MyStakingPool',
    sponsorLogo: 'https://mypool.io/logo.png',
    targetUrl: 'https://mypool.io',
    callToAction: 'Learn More',
  },
  payment: {
    model: 'cpc',
    rateCpc: 0.75,
    budget: 500,
  },
});
```

### Get Ad for Display

```typescript
const context = {
  sessionId: 'sess-123',
  userId: 'user-456',
  userConsented: true,
  doNotTrack: false,
  currentAction: 'balance-check',
  placement: 'dashboard',
};

const ad = await adsManager.getAdForContext(context);

if (ad) {
  // Display ad
  await adsManager.recordImpression({ adId: ad.adId, context });
  
  // User clicks ad
  await adsManager.recordClick({ adId: ad.adId, context });
}
```

### Process Payment

```typescript
const paymentProcessor = wali.getPaymentProcessor();

// Create payment intent
const intent = await paymentProcessor.createPaymentIntent({
  dappId: 'dapp-123',
  amount: 99,
  currency: 'USD',
  description: 'Basic tier subscription',
  paymentMethod: 'cardano',
});

console.log('Pay to:', intent.cardanoPaymentAddress);
console.log('Amount:', intent.expectedAmount, 'lovelace');

// Verify payment
const transaction = await paymentProcessor.verifyCardanoPayment({
  intentId: intent.intentId,
  txHash: '0x123...',
  amount: intent.expectedAmount!,
  confirmations: 5,
});

if (transaction?.status === 'confirmed') {
  console.log('Payment confirmed!');
}
```

## Features

### dApp Registry

- **Registration**: Easy onboarding with trial period
- **Tiers**: Basic ($99), Premium ($299), Enterprise (custom)
- **Feature Gating**: Control access based on tier
- **Usage Tracking**: Monitor connected users
- **Analytics**: Utilization, expiration tracking
- **Auto-expiration**: Handle overdue subscriptions

### Ads Manager

- **Privacy-First**: Respect Do Not Track, require consent
- **Multiple Formats**: Banner, native, sponsored
- **Smart Targeting**: Contextual, geographic, interest-based
- **Frequency Limits**: Session and daily caps
- **Performance Tracking**: Impressions, clicks, CTR
- **Revenue Models**: CPM, CPC, flat rate

### Payment Processor

- **Cardano Native**: Low-fee, instant settlement
- **Fiat Support**: Stripe integration (optional)
- **Subscriptions**: Recurring billing, auto-renewal
- **Webhooks**: Real-time payment notifications
- **Exchange Rates**: ADA/USD conversion
- **Revenue Analytics**: Total revenue, MRR tracking

## Configuration

### Disable Monetization

```typescript
const wali = new WaliEngine({
  monetization: {
    dappIntegrations: { enabled: false },
    advertisements: { enabled: false },
  },
});
```

### Privacy-Only Mode (No Ads)

```typescript
const wali = new WaliEngine({
  monetization: {
    advertisements: {
      enabled: true,
      respectDoNotTrack: true, // Users with DNT see no ads
      requireUserConsent: true, // Users must opt-in
    },
  },
});
```

### Cardano-Only Payments

```typescript
const wali = new WaliEngine({
  monetization: {
    payments: {
      acceptCardano: true,
      acceptFiat: false, // Disable Stripe
      cardanoPaymentAddress: 'addr1...',
    },
  },
});
```

## Type Safety

All monetization types are fully typed for TypeScript:

```typescript
import {
  DAppIntegration,
  Advertisement,
  PaymentTransaction,
  MonetizationConfig,
} from './monetization/types';
```

## Best Practices

### For wAli Developers

1. **Test Ad Placements**: Ensure non-intrusive UX
2. **Monitor Performance**: Track CTR, user feedback
3. **Privacy Audits**: Regular compliance checks
4. **Cache Ads**: Don't fetch on every render
5. **Error Handling**: Graceful fallbacks if monetization fails

### For dApp Developers

1. **Start with Trial**: Test integration before paying
2. **Monitor Usage**: Upgrade before hitting limits
3. **Use Webhooks**: Don't poll for payment status
4. **Cardano Payments**: Lower fees, instant settlement
5. **API Best Practices**: Cache, retry, handle rate limits

### For Advertisers

1. **Relevant Content**: Ads should help crypto users
2. **Quality Creatives**: Clear, honest messaging
3. **Mobile-First**: Most users are on mobile
4. **Track Performance**: Use UTM parameters
5. **Respect Privacy**: No personal data requests

## Testing

### Mock Implementations

```typescript
import { DAppRegistry } from './monetization/dapp-registry';

// In-memory registry for testing
const registry = new DAppRegistry({
  storageBackend: 'memory',
  trialDurationDays: 1, // Shorter for testing
});

const dapp = await registry.registerDApp({
  name: 'Test App',
  tier: 'basic',
});

expect(dapp.paymentStatus).toBe('trial');
```

### Simulate Payments

```typescript
import { PaymentProcessor } from './monetization/payment-processor';

const processor = new PaymentProcessor({
  cardanoNetwork: 'testnet',
  adaUsdRate: 0.5, // Fixed rate for testing
});

const intent = await processor.createPaymentIntent({
  amount: 99,
  currency: 'USD',
  paymentMethod: 'cardano',
});

// Simulate successful payment
const tx = await processor.verifyCardanoPayment({
  intentId: intent.intentId,
  txHash: 'test-hash-123',
  amount: intent.expectedAmount!,
  confirmations: 3,
});

expect(tx?.status).toBe('confirmed');
```

## Documentation

- **[MONETIZATION.md](../../MONETIZATION.md)** - Revenue overview and projections
- **[DAPP_INTEGRATION_GUIDE.md](../../DAPP_INTEGRATION_GUIDE.md)** - How to integrate your dApp
- **[ADVERTISEMENT_POLICY.md](../../ADVERTISEMENT_POLICY.md)** - Ad guidelines and privacy policy

## Support

- **Issues**: GitHub Issues
- **Email**: monetization@wali.app
- **Discord**: #monetization channel

---

**Built with 💰 by the wAli team** 🦭

*Sustainable growth, without compromising on friendliness!*
