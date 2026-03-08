"use strict";
/**
 * Monetization Type Definitions
 * Supports dApp integrations and advertisement infrastructure
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_TIERS = void 0;
/**
 * Default tier configurations
 */
exports.DEFAULT_TIERS = [
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
exports.default = {
    DEFAULT_TIERS: exports.DEFAULT_TIERS,
};
