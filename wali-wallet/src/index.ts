/**
 * Core Wallet Engine - Entry Point
 * Exports all public APIs
 */

export { WalletEngine, WalletEngineConfig } from './wallet-engine';
export { CardanoWallet } from './cardano/wallet';
export { CardanoAPI, CardanoAPIConfig } from './cardano/api';
export { BitcoinWallet, BitcoinAddressType } from './bitcoin/wallet';
export { BitcoinAPI, BitcoinAPIConfig } from './bitcoin/api';

export * from './types';
export { 
  SecureContainer, 
  validateCardanoAddress, 
  validateBitcoinAddress,
  sanitizeError 
} from './utils/security';
