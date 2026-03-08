/**
 * Night/Midnight blockchain wallet creation and management
 * 
 * This module handles:
 * - Night wallet generation
 * - Keypair management
 * - Address derivation
 */

import * as crypto from 'crypto';
import * as ed25519 from '@noble/ed25519';
import { NightWallet, NightWalletConfig } from './types';
import { wipeBuffer } from '../utils/security';

/**
 * Generate a new Night/Midnight wallet
 * 
 * Note: This is a simplified implementation. In production, you would use
 * the official Midnight SDK for wallet creation.
 * 
 * @param config Network configuration
 * @returns Night wallet with address and public key
 */
export async function createNightWallet(
  config: NightWalletConfig
): Promise<NightWallet> {
  // Generate Ed25519 keypair using browser-compatible library
  const privateKey = ed25519.utils.randomPrivateKey();
  const publicKey = await ed25519.getPublicKeyAsync(privateKey);
  
  // Derive address from public key
  // In a real implementation, this would follow Midnight's address format
  const pubKeyBuffer = Buffer.from(publicKey);
  const addressHash = crypto.createHash('sha256').update(pubKeyBuffer).digest();
  
  // Create bech32-like address (simplified)
  const networkPrefix = config.network === 'mainnet' ? 'night1' : 'nighttest1';
  const addressSuffix = addressHash.toString('hex').substring(0, 58);
  const address = `${networkPrefix}${addressSuffix}`;
  
  // Store only public key (private key should be securely stored separately)
  const wallet: NightWallet = {
    address,
    publicKey: pubKeyBuffer.toString('hex')
  };
  
  // In production, private key would be encrypted and stored securely
  // For now, we'll note that it exists but don't expose it
  console.log('[INFO] Night wallet created successfully');
  console.log('[INFO] Address:', address);
  console.log('[SECURITY] Private key generated but not exposed in return value');
  
  return wallet;
}

/**
 * Derive Night wallet from existing seed
 * This would be used if you want to derive a Night wallet from
 * the same seed as Cardano/Bitcoin wallets
 * 
 * @param seed Master seed (from BIP39 mnemonic)
 * @param config Network configuration
 * @returns Night wallet
 */
export async function deriveNightWallet(
  seed: Buffer,
  config: NightWalletConfig
): Promise<NightWallet> {
  try {
    // Derive Night-specific key from master seed
    // Path: m/44'/1815'/0'/0/0 (using Cardano's coin type for now)
    const pathHash = crypto.createHash('sha256')
      .update(seed)
      .update('night-chain-derivation')
      .digest();
    
    // Generate deterministic keypair from derived seed using @noble/ed25519
    // Note: In production, use proper BIP32/BIP44 derivation
    const privateKey = pathHash.slice(0, 32); // Use first 32 bytes as private key
    const publicKey = await ed25519.getPublicKeyAsync(privateKey);
    
    const pubKeyBuffer = Buffer.from(publicKey);
    const addressHash = crypto.createHash('sha256')
      .update(pubKeyBuffer)
      .update(pathHash)
      .digest();
    
    const networkPrefix = config.network === 'mainnet' ? 'night1' : 'nighttest1';
    const addressSuffix = addressHash.toString('hex').substring(0, 58);
    const address = `${networkPrefix}${addressSuffix}`;
    
    return {
      address,
      publicKey: pubKeyBuffer.toString('hex')
    };
  } finally {
    // Wipe sensitive data
    wipeBuffer(seed);
  }
}

/**
 * Validate Night wallet address format
 */
export function validateNightAddress(address: string): boolean {
  // Check format: night1 or nighttest1 followed by 58 hex characters
  const mainnetPattern = /^night1[a-f0-9]{58}$/;
  const testnetPattern = /^nighttest1[a-f0-9]{58}$/;
  
  return mainnetPattern.test(address) || testnetPattern.test(address);
}

/**
 * Get network from address
 */
export function getNetworkFromAddress(address: string): 'mainnet' | 'testnet' | null {
  if (address.startsWith('night1')) return 'mainnet';
  if (address.startsWith('nighttest1')) return 'testnet';
  return null;
}

/**
 * Initialize Night wallet client
 * In production, this would connect to Midnight RPC node
 */
export class NightWalletClient {
  private config: NightWalletConfig;
  private wallet: NightWallet | null = null;
  
  constructor(config: NightWalletConfig) {
    this.config = config;
  }
  
  async initialize(): Promise<void> {
    console.log('[INFO] Initializing Night wallet client');
    console.log('[INFO] Network:', this.config.network);
    console.log('[INFO] RPC Endpoint:', this.config.rpcEndpoint || 'default');
    
    // In production, establish connection to Midnight node
    // For now, just validate config
    if (!this.config.network) {
      throw new Error('Network configuration required');
    }
  }
  
  async createWallet(): Promise<NightWallet> {
    const wallet = await createNightWallet(this.config);
    this.wallet = wallet;
    return wallet;
  }
  
  getWallet(): NightWallet | null {
    return this.wallet;
  }
  
  async disconnect(): Promise<void> {
    console.log('[INFO] Disconnecting Night wallet client');
    this.wallet = null;
  }
}
