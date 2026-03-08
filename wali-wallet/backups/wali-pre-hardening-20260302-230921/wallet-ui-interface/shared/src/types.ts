/**
 * Shared type definitions for wallet UI interface
 */

export type Chain = 'cardano' | 'bitcoin';
export type AssetType = 'native' | 'token' | 'nft';

export interface Asset {
  chain: Chain;
  type: AssetType;
  symbol: string;
  policyId?: string;
  assetName?: string;
  decimals: number;
  balance: string;
  metadata?: {
    name?: string;
    description?: string;
    image?: string;
    [key: string]: any;
  };
}

export interface Address {
  address: string;
  type: 'address' | 'handle';
  chain: Chain;
  metadata?: {
    handle?: string;
    displayName?: string;
  };
}

export interface TransactionIntent {
  type: 'send' | 'delegate' | 'vote' | 'swap' | 'mint' | 'burn' | 'create_wallet' | 'import_wallet' | 'show_balance' | 'show_history';
  chain: Chain;
  from?: string;
  to?: Address;
  amount?: string;
  asset?: Asset;
  metadata?: Record<string, any>;
}

export interface ParsedCommand {
  intent: TransactionIntent;
  confidence: number;
  ambiguities: Ambiguity[];
  rawInput: string;
}

export interface Ambiguity {
  field: string;
  message: string;
  suggestions?: string[];
}

export interface TransactionPreview {
  intent: TransactionIntent;
  fee: string;
  feeAsset: Asset;
  totalCost: string;
  humanReadable: string;
  warnings: string[];
  metadata?: Record<string, any>;
}

export interface DAppConnectionRequest {
  dappId: string;
  dappName: string;
  dappUrl: string;
  requestedPermissions: Permission[];
  metadata?: {
    icon?: string;
    description?: string;
  };
}

export interface Permission {
  type: 'read_balance' | 'read_address' | 'sign_transaction' | 'sign_data';
  description: string;
  required: boolean;
}

export interface DAppConnection {
  dappId: string;
  dappName: string;
  dappUrl: string;
  permissions: Permission[];
  connectedAt: number;
  lastUsed: number;
}

export interface WalletState {
  isInitialized: boolean;
  isLocked: boolean;
  activeAccount?: string;
  accounts: Account[];
  assets: Asset[];
  connections: DAppConnection[];
}

export interface Account {
  id: string;
  name: string;
  chain: Chain;
  addresses: {
    receiving: string;
    change?: string;
  };
  balance: {
    confirmed: string;
    pending: string;
  };
}

export interface CommandResponse {
  success: boolean;
  message: string;
  data?: any;
  requiresConfirmation?: boolean;
  preview?: TransactionPreview;
  suggestions?: string[];
}

export interface LoadingState {
  isLoading: boolean;
  operation?: string;
  progress?: number;
}

export interface ErrorState {
  hasError: boolean;
  message?: string;
  recoveryAction?: string;
  code?: string;
}
