/**
 * Core type definitions for the wallet engine
 */

export type NetworkType = 'mainnet' | 'testnet';

export interface WalletCreationResult {
  mnemonic: Uint8Array; // BIP39 mnemonic as Uint8Array - WIPE FROM MEMORY AFTER USE
  addresses: {
    cardano?: string;
    bitcoin?: string;
  };
}

export interface WalletImportOptions {
  mnemonic: Uint8Array; // BIP39 mnemonic as Uint8Array - WIPE FROM MEMORY AFTER USE
  chains: ('cardano' | 'bitcoin')[];
  network?: NetworkType;
}

export interface CardanoAddress {
  address: string;
  paymentKey: string; // Public key only
  stakeKey?: string; // Public key only
}

export interface BitcoinAddress {
  address: string;
  publicKey: string;
  derivationPath: string;
}

export interface Balance {
  chain: 'cardano' | 'bitcoin';
  address: string;
  native: {
    amount: string; // String to handle large numbers
    symbol: string; // ADA or BTC
    decimals: number;
  };
  tokens?: TokenBalance[];
}

export interface TokenBalance {
  policyId?: string; // Cardano only
  assetName?: string; // Cardano only
  name: string;
  symbol: string;
  amount: string;
  decimals: number;
  metadata?: any;
}

export interface TransactionInput {
  txHash: string;
  index: number;
  amount: string;
}

export interface TransactionOutput {
  address: string;
  amount: string;
  tokens?: Array<{
    policyId?: string;
    assetName?: string;
    amount: string;
  }>;
}

export interface Transaction {
  chain: 'cardano' | 'bitcoin';
  hash: string;
  timestamp: number;
  status: 'pending' | 'confirmed' | 'failed';
  inputs: TransactionInput[];
  outputs: TransactionOutput[];
  fee: string;
  confirmations: number;
}

export interface TransactionBuildRequest {
  chain: 'cardano' | 'bitcoin';
  from: string;
  to: string;
  amount: string; // In lovelace or satoshis
  tokens?: Array<{
    policyId?: string;
    assetName?: string;
    amount: string;
  }>;
  metadata?: any;
}

export interface UnsignedTransaction {
  chain: 'cardano' | 'bitcoin';
  raw: string; // Serialized unsigned transaction
  fee: string;
  preview: {
    from: string;
    to: string;
    amount: string;
    fee: string;
    total: string;
    tokens?: TokenBalance[];
  };
}

export interface SignedTransaction {
  chain: 'cardano' | 'bitcoin';
  txHash: string;
  raw: string; // Serialized signed transaction
}

export interface FeeEstimate {
  chain: 'cardano' | 'bitcoin';
  slow: string;
  medium: string;
  fast: string;
  unit: string; // 'lovelace' or 'satoshis'
}

export interface WalletError {
  code: string;
  message: string;
  details?: any;
}

export interface ADAHandle {
  handle: string; // e.g., "$alice"
  address: string; // Resolved addr1...
  metadata?: any;
}

// Internal types for sensitive operations
export interface SensitiveKeyMaterial {
  privateKey: Buffer;
  // Must be explicitly wiped after use
}

export interface SecureWipeTarget {
  wipe(): void;
}
