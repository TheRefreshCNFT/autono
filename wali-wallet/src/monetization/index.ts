/**
 * Monetization Module
 * Centralized exports for monetization infrastructure
 */

export * from './types';
export { DAppRegistry } from './dapp-registry';
export { AdsManager } from './ads-manager';
export { PaymentProcessor } from './payment-processor';

export { default as DAppRegistryClass } from './dapp-registry';
export { default as AdsManagerClass } from './ads-manager';
export { default as PaymentProcessorClass } from './payment-processor';
