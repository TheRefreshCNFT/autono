/**
 * Blockfrost API Integration for Cardano
 * Production-ready API client with retry logic, caching, and error handling
 * 
 * Rate limiting: Managed by Blockfrost plan - no artificial client-side limits.
 * Monitor your API usage in the Blockfrost dashboard and upgrade plan as needed.
 * 
 * @see https://docs.blockfrost.io/
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import { Balance, Transaction, TokenBalance } from '../types';

export interface BlockfrostConfig {
  projectId: string;
  network: 'mainnet' | 'testnet';
  maxRetries?: number;
  retryDelayMs?: number;
  cacheEnabled?: boolean;
  cacheTTL?: number;
}

export interface BlockfrostUTXO {
  txHash: string;
  index: number;
  amount: string;
  assets?: Array<{
    unit: string;
    quantity: string;
  }>;
}

export interface BlockfrostAssetMetadata {
  policyId: string;
  assetName: string;
  assetNameAscii: string;
  fingerprint: string;
  quantity: string;
  metadata?: {
    name?: string;
    description?: string;
    ticker?: string;
    decimals?: number;
    logo?: string;
  };
}

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

/**
 * Blockfrost API Client for Cardano blockchain interactions
 */
export class BlockfrostAPI {
  private client: AxiosInstance;
  private config: Required<BlockfrostConfig>;
  private cache: Map<string, CacheEntry<any>>;
  private baseURL: string;

  constructor(config: BlockfrostConfig) {
    this.config = {
      projectId: config.projectId,
      network: config.network,
      maxRetries: config.maxRetries ?? 3,
      retryDelayMs: config.retryDelayMs ?? 1000,
      cacheEnabled: config.cacheEnabled ?? true,
      cacheTTL: config.cacheTTL ?? 30000, // 30 seconds default
    };

    this.baseURL = config.network === 'mainnet'
      ? 'https://cardano-mainnet.blockfrost.io/api/v0'
      : 'https://cardano-testnet.blockfrost.io/api/v0';

    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'project_id': this.config.projectId,
      },
      timeout: 30000, // 30 second timeout
    });

    this.cache = new Map();

    // Setup request interceptor for logging (without exposing API key)
    this.client.interceptors.request.use(
      (config) => {
        // Never log the API key
        const sanitizedHeaders = { ...config.headers };
        if (sanitizedHeaders['project_id']) {
          sanitizedHeaders['project_id'] = '[REDACTED]';
        }
        return config;
      },
      (error) => Promise.reject(error)
    );
  }

  /**
   * Get balance for a Cardano address (ADA + all native tokens)
   */
  async getBalance(address: string): Promise<Balance> {
    const cacheKey = `balance:${address}`;
    const cached = this.getFromCache<Balance>(cacheKey);
    if (cached) return cached;

    try {
      const addressInfo = await this.retryRequest<any>(
        () => this.client.get(`/addresses/${address}`)
      );

      const data = addressInfo.data;
      
      // Extract ADA balance (lovelace)
      const lovelaceAmount = data.amount?.find((a: any) => a.unit === 'lovelace')?.quantity || '0';

      // Extract native tokens
      const tokens: TokenBalance[] = [];
      if (data.amount) {
        for (const asset of data.amount) {
          if (asset.unit !== 'lovelace') {
            const policyId = asset.unit.substring(0, 56);
            const assetNameHex = asset.unit.substring(56);
            const assetName = this.hexToString(assetNameHex) || assetNameHex;

            tokens.push({
              policyId,
              assetName: assetNameHex,
              name: assetName,
              symbol: assetName,
              amount: asset.quantity,
              decimals: 0, // Will be enriched by metadata if available
            });
          }
        }
      }

      const balance: Balance = {
        chain: 'cardano',
        address,
        native: {
          amount: lovelaceAmount,
          symbol: 'ADA',
          decimals: 6,
        },
        tokens: tokens.length > 0 ? tokens : undefined,
      };

      this.setCache(cacheKey, balance);
      return balance;
    } catch (error) {
      throw this.handleError(error, 'Failed to fetch balance');
    }
  }

  /**
   * Get UTXOs for an address
   */
  async getUTXOs(address: string): Promise<BlockfrostUTXO[]> {
    const cacheKey = `utxos:${address}`;
    const cached = this.getFromCache<BlockfrostUTXO[]>(cacheKey);
    if (cached) return cached;

    try {
      const response = await this.retryRequest<any>(
        () => this.client.get(`/addresses/${address}/utxos`)
      );

      const utxos: BlockfrostUTXO[] = response.data.map((utxo: any) => ({
        txHash: utxo.tx_hash,
        index: utxo.output_index,
        amount: utxo.amount.find((a: any) => a.unit === 'lovelace')?.quantity || '0',
        assets: utxo.amount
          .filter((a: any) => a.unit !== 'lovelace')
          .map((a: any) => ({
            unit: a.unit,
            quantity: a.quantity,
          })),
      }));

      this.setCache(cacheKey, utxos);
      return utxos;
    } catch (error) {
      throw this.handleError(error, 'Failed to fetch UTXOs');
    }
  }

  /**
   * Submit a signed transaction to the network
   */
  async submitTransaction(signedTxCBOR: string): Promise<string> {
    try {
      const txBuffer = Buffer.from(signedTxCBOR, 'hex');
      
      const response = await this.retryRequest<any>(
        () => this.client.post('/tx/submit', txBuffer, {
          headers: {
            'Content-Type': 'application/cbor',
          },
        })
      );

      // Blockfrost returns the transaction hash on successful submission
      return response.data;
    } catch (error) {
      throw this.handleError(error, 'Failed to submit transaction');
    }
  }

  /**
   * Resolve ADA Handle ($handle) to Cardano address
   */
  async resolveAdaHandle(handle: string): Promise<string | null> {
    // Remove $ prefix if present
    const cleanHandle = handle.startsWith('$') ? handle.substring(1) : handle;
    
    const cacheKey = `handle:${cleanHandle}`;
    const cached = this.getFromCache<string | null>(cacheKey);
    if (cached !== undefined) return cached;

    try {
      // ADA Handle policy ID (mainnet)
      const HANDLE_POLICY_ID = 'f0ff48bbb7bbe9d59a40f1ce90e9e9d0ff5002ec48f232b49ca0fb9a';
      const handleHex = Buffer.from(cleanHandle).toString('hex');
      const assetId = `${HANDLE_POLICY_ID}${handleHex}`;

      const response = await this.retryRequest<any>(
        () => this.client.get(`/assets/${assetId}/addresses`)
      );

      if (response.data && response.data.length > 0) {
        const address = response.data[0].address;
        this.setCache(cacheKey, address, 300000); // Cache handles for 5 minutes
        return address;
      }

      this.setCache(cacheKey, null, 300000);
      return null;
    } catch (error: any) {
      // 404 means handle not found - this is not an error
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        this.setCache(cacheKey, null, 300000);
        return null;
      }
      throw this.handleError(error, 'Failed to resolve ADA handle');
    }
  }

  /**
   * Get transaction history for an address
   */
  async getTransactionHistory(
    address: string,
    limit: number = 50,
    page: number = 1
  ): Promise<Transaction[]> {
    const cacheKey = `txHistory:${address}:${limit}:${page}`;
    const cached = this.getFromCache<Transaction[]>(cacheKey);
    if (cached) return cached;

    try {
      // Get transaction hashes for the address
      const response = await this.retryRequest<any>(
        () => this.client.get(`/addresses/${address}/transactions`, {
          params: {
            count: limit,
            page,
            order: 'desc',
          },
        })
      );

      const txHashes = response.data.map((tx: any) => tx.tx_hash);

      // Fetch details for each transaction
      const transactions: Transaction[] = [];
      for (const txHash of txHashes) {
        try {
          const txDetail = await this.getTransactionDetail(txHash);
          transactions.push(txDetail);
        } catch (error) {
          // Skip transactions that fail to fetch
          console.error(`Failed to fetch transaction ${txHash}:`, error);
        }
      }

      this.setCache(cacheKey, transactions, 60000); // Cache for 1 minute
      return transactions;
    } catch (error) {
      throw this.handleError(error, 'Failed to fetch transaction history');
    }
  }

  /**
   * Get detailed transaction information
   */
  async getTransactionDetail(txHash: string): Promise<Transaction> {
    const cacheKey = `tx:${txHash}`;
    const cached = this.getFromCache<Transaction>(cacheKey);
    if (cached) return cached;

    try {
      const response = await this.retryRequest<any>(
        () => this.client.get(`/txs/${txHash}`)
      );

      const data = response.data;

      const transaction: Transaction = {
        chain: 'cardano',
        hash: txHash,
        timestamp: data.block_time * 1000,
        status: data.block ? 'confirmed' : 'pending',
        inputs: [],
        outputs: [],
        fee: data.fees || '0',
        confirmations: data.block ? 100 : 0, // Simplified - could calculate actual confirmations
      };

      this.setCache(cacheKey, transaction, 300000); // Cache transactions for 5 minutes
      return transaction;
    } catch (error) {
      throw this.handleError(error, 'Failed to fetch transaction detail');
    }
  }

  /**
   * Get asset metadata
   */
  async getAssetMetadata(assetId: string): Promise<BlockfrostAssetMetadata | null> {
    const cacheKey = `assetMetadata:${assetId}`;
    const cached = this.getFromCache<BlockfrostAssetMetadata | null>(cacheKey);
    if (cached !== undefined) return cached;

    try {
      const response = await this.retryRequest<any>(
        () => this.client.get(`/assets/${assetId}`)
      );

      const data = response.data;
      
      const metadata: BlockfrostAssetMetadata = {
        policyId: data.policy_id,
        assetName: data.asset_name,
        assetNameAscii: this.hexToString(data.asset_name) || data.asset_name,
        fingerprint: data.fingerprint,
        quantity: data.quantity,
        metadata: data.onchain_metadata ? {
          name: data.onchain_metadata.name,
          description: data.onchain_metadata.description,
          ticker: data.onchain_metadata.ticker,
          decimals: data.onchain_metadata.decimals,
          logo: data.onchain_metadata.logo,
        } : undefined,
      };

      this.setCache(cacheKey, metadata, 3600000); // Cache metadata for 1 hour
      return metadata;
    } catch (error: any) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        this.setCache(cacheKey, null, 3600000);
        return null;
      }
      throw this.handleError(error, 'Failed to fetch asset metadata');
    }
  }

  /**
   * Estimate transaction fees
   */
  async estimateFees(): Promise<{
    slow: string;
    medium: string;
    fast: string;
  }> {
    // Cardano has relatively stable fees based on transaction size
    // These are typical values in lovelace for average transactions
    return {
      slow: '170000',   // ~0.17 ADA
      medium: '200000', // ~0.20 ADA
      fast: '250000',   // ~0.25 ADA
    };
  }

  /**
   * Get latest block information (for TTL calculation)
   */
  async getLatestBlock(): Promise<{ slot: number; height: number; hash: string }> {
    const cacheKey = 'latestBlock';
    const cached = this.getFromCache<{ slot: number; height: number; hash: string }>(cacheKey);
    if (cached) return cached;

    try {
      const response = await this.retryRequest<any>(
        () => this.client.get('/blocks/latest')
      );

      const data = response.data;
      const blockInfo = {
        slot: data.slot || 0,
        height: data.height || 0,
        hash: data.hash || '',
      };

      this.setCache(cacheKey, blockInfo, 10000); // Cache for 10 seconds
      return blockInfo;
    } catch (error) {
      throw this.handleError(error, 'Failed to fetch latest block');
    }
  }

  /**
   * Get protocol parameters (needed for transaction building)
   */
  async getProtocolParameters(): Promise<any> {
    const cacheKey = 'protocolParams';
    const cached = this.getFromCache<any>(cacheKey);
    if (cached) return cached;

    try {
      const response = await this.retryRequest<any>(
        () => this.client.get('/epochs/latest/parameters')
      );

      this.setCache(cacheKey, response.data, 3600000); // Cache for 1 hour
      return response.data;
    } catch (error) {
      throw this.handleError(error, 'Failed to fetch protocol parameters');
    }
  }

  /**
   * Retry mechanism with exponential backoff for transient failures
   * Note: Retries server errors and network issues, NOT client-side rate limiting.
   * Rate limits are managed by your Blockfrost plan - upgrade if you hit limits frequently.
   */
  private async retryRequest<T>(
    request: () => Promise<T>,
    retries: number = this.config.maxRetries
  ): Promise<T> {
    try {
      return await request();
    } catch (error: any) {
      if (retries > 0 && this.shouldRetry(error)) {
        const delay = this.config.retryDelayMs * (this.config.maxRetries - retries + 1);
        await this.sleep(delay);
        return this.retryRequest(request, retries - 1);
      }
      throw error;
    }
  }

  /**
   * Determine if error is retryable (server/network errors only)
   * Rate limit (429) errors are retried to handle transient Blockfrost congestion,
   * but no artificial client-side throttling is applied.
   */
  private shouldRetry(error: any): boolean {
    if (!axios.isAxiosError(error)) return false;

    const status = error.response?.status;
    
    // Retry on server errors and network errors
    return (
      status === 429 || // Rate limit - let Blockfrost handle limits, we just retry
      status === 500 || // Internal server error
      status === 502 || // Bad gateway
      status === 503 || // Service unavailable
      status === 504 || // Gateway timeout
      error.code === 'ECONNABORTED' ||
      error.code === 'ETIMEDOUT'
    );
  }

  /**
   * Sleep helper for retry delays
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Get data from cache if valid
   */
  private getFromCache<T>(key: string): T | undefined {
    if (!this.config.cacheEnabled) return undefined;

    const entry = this.cache.get(key);
    if (!entry) return undefined;

    const now = Date.now();
    if (now - entry.timestamp > this.config.cacheTTL) {
      this.cache.delete(key);
      return undefined;
    }

    return entry.data as T;
  }

  /**
   * Set data in cache
   */
  private setCache<T>(key: string, data: T, ttl?: number): void {
    if (!this.config.cacheEnabled) return;

    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    });

    // Auto-cleanup after TTL
    const cacheTTL = ttl || this.config.cacheTTL;
    setTimeout(() => this.cache.delete(key), cacheTTL);
  }

  /**
   * Clear cache (useful for testing or force refresh)
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Convert hex string to UTF-8 string
   */
  private hexToString(hex: string): string | null {
    try {
      return Buffer.from(hex, 'hex').toString('utf8');
    } catch {
      return null;
    }
  }

  /**
   * Handle and format errors
   */
  private handleError(error: any, context: string): Error {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status;
      const message = error.response?.data?.message || error.message;
      
      // Never expose API key in errors
      const sanitizedMessage = message.replace(this.config.projectId, '[REDACTED]');
      
      if (status === 429) {
        return new Error(`${context}: Rate limit exceeded. Please try again later.`);
      }
      
      if (status === 403) {
        return new Error(`${context}: Invalid or expired API key.`);
      }
      
      if (status === 404) {
        return new Error(`${context}: Resource not found.`);
      }
      
      return new Error(`${context}: ${sanitizedMessage}`);
    }

    return new Error(`${context}: ${error.message || 'Unknown error'}`);
  }

  /**
   * Get API health status
   */
  async healthCheck(): Promise<{ healthy: boolean; network: string }> {
    try {
      const response = await this.client.get('/health');
      return {
        healthy: response.data.is_healthy || false,
        network: this.config.network,
      };
    } catch (error) {
      return {
        healthy: false,
        network: this.config.network,
      };
    }
  }
}

export default BlockfrostAPI;
