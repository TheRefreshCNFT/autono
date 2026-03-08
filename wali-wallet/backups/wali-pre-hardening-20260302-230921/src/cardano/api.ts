/**
 * Cardano blockchain API interactions (Blockfrost or Koios)
 */

import axios from 'axios';
import { Balance, Transaction, TokenBalance } from '../types';

export interface CardanoAPIConfig {
  provider: 'blockfrost' | 'koios';
  apiKey?: string;
  network: 'mainnet' | 'testnet';
}

export class CardanoAPI {
  private config: CardanoAPIConfig;
  private baseURL: string;

  constructor(config: CardanoAPIConfig) {
    this.config = config;
    
    if (config.provider === 'blockfrost') {
      this.baseURL = config.network === 'mainnet'
        ? 'https://cardano-mainnet.blockfrost.io/api/v0'
        : 'https://cardano-testnet.blockfrost.io/api/v0';
    } else {
      this.baseURL = config.network === 'mainnet'
        ? 'https://api.koios.rest/api/v1'
        : 'https://testnet.koios.rest/api/v1';
    }
  }

  /**
   * Get balance for a Cardano address
   */
  async getBalance(address: string): Promise<Balance> {
    try {
      const headers = this.config.apiKey 
        ? { 'project_id': this.config.apiKey }
        : {};

      const response = await axios.get(
        `${this.baseURL}/addresses/${address}`,
        { headers }
      );

      const data = response.data;
      const lovelace = data.amount?.find((a: any) => a.unit === 'lovelace')?.quantity || '0';

      // Parse tokens
      const tokens: TokenBalance[] = [];
      if (data.amount) {
        for (const asset of data.amount) {
          if (asset.unit !== 'lovelace') {
            const policyId = asset.unit.substring(0, 56);
            const assetName = asset.unit.substring(56);

            tokens.push({
              policyId,
              assetName,
              name: this.hexToString(assetName) || assetName,
              symbol: this.hexToString(assetName) || assetName,
              amount: asset.quantity,
              decimals: 0 // Will need to fetch from metadata for accurate decimals
            });
          }
        }
      }

      return {
        chain: 'cardano',
        address,
        native: {
          amount: lovelace,
          symbol: 'ADA',
          decimals: 6
        },
        tokens: tokens.length > 0 ? tokens : undefined
      };
    } catch (error: any) {
      throw new Error(`Failed to fetch Cardano balance: ${error.message}`);
    }
  }

  /**
   * Get transaction history for an address
   */
  async getTransactionHistory(
    address: string,
    limit: number = 50
  ): Promise<Transaction[]> {
    try {
      const headers = this.config.apiKey 
        ? { 'project_id': this.config.apiKey }
        : {};

      const response = await axios.get(
        `${this.baseURL}/addresses/${address}/transactions`,
        { 
          headers,
          params: { count: limit, order: 'desc' }
        }
      );

      const txHashes = response.data.map((tx: any) => tx.tx_hash);
      const transactions: Transaction[] = [];

      // Fetch detailed info for each transaction
      for (const txHash of txHashes.slice(0, limit)) {
        const txDetail = await this.getTransactionDetail(txHash);
        transactions.push(txDetail);
      }

      return transactions;
    } catch (error: any) {
      throw new Error(`Failed to fetch transaction history: ${error.message}`);
    }
  }

  /**
   * Get detailed transaction information
   */
  async getTransactionDetail(txHash: string): Promise<Transaction> {
    try {
      const headers = this.config.apiKey 
        ? { 'project_id': this.config.apiKey }
        : {};

      const response = await axios.get(
        `${this.baseURL}/txs/${txHash}`,
        { headers }
      );

      const data = response.data;

      return {
        chain: 'cardano',
        hash: txHash,
        timestamp: data.block_time * 1000,
        status: data.block ? 'confirmed' : 'pending',
        inputs: [],
        outputs: [],
        fee: data.fees || '0',
        confirmations: data.block_height ? 100 : 0 // Simplified
      };
    } catch (error: any) {
      throw new Error(`Failed to fetch transaction detail: ${error.message}`);
    }
  }

  /**
   * Get UTXOs for an address
   */
  async getUTXOs(address: string): Promise<Array<{
    txHash: string;
    index: number;
    amount: string;
  }>> {
    try {
      const headers = this.config.apiKey 
        ? { 'project_id': this.config.apiKey }
        : {};

      const response = await axios.get(
        `${this.baseURL}/addresses/${address}/utxos`,
        { headers }
      );

      return response.data.map((utxo: any) => ({
        txHash: utxo.tx_hash,
        index: utxo.output_index,
        amount: utxo.amount.find((a: any) => a.unit === 'lovelace')?.quantity || '0'
      }));
    } catch (error: any) {
      throw new Error(`Failed to fetch UTXOs: ${error.message}`);
    }
  }

  /**
   * Submit a signed transaction
   */
  async submitTransaction(signedTxHex: string): Promise<string> {
    try {
      const headers = {
        'Content-Type': 'application/cbor',
        ...(this.config.apiKey ? { 'project_id': this.config.apiKey } : {})
      };

      const response = await axios.post(
        `${this.baseURL}/tx/submit`,
        Buffer.from(signedTxHex, 'hex'),
        { headers }
      );

      return response.data;
    } catch (error: any) {
      throw new Error(`Failed to submit transaction: ${error.message}`);
    }
  }

  /**
   * Resolve ADA handle to address
   */
  async resolveADAHandle(handle: string): Promise<string | null> {
    try {
      // Remove $ prefix if present
      const cleanHandle = handle.startsWith('$') ? handle.substring(1) : handle;

      // ADA Handle uses a specific policy ID
      const HANDLE_POLICY_ID = 'f0ff48bbb7bbe9d59a40f1ce90e9e9d0ff5002ec48f232b49ca0fb9a';
      const handleHex = Buffer.from(cleanHandle).toString('hex');

      const headers = this.config.apiKey 
        ? { 'project_id': this.config.apiKey }
        : {};

      const response = await axios.get(
        `${this.baseURL}/assets/${HANDLE_POLICY_ID}${handleHex}/addresses`,
        { headers }
      );

      if (response.data && response.data.length > 0) {
        return response.data[0].address;
      }

      return null;
    } catch (error: any) {
      // Handle not found is not an error
      return null;
    }
  }

  /**
   * Estimate current fees
   */
  async estimateFees(): Promise<{
    slow: string;
    medium: string;
    fast: string;
  }> {
    // Cardano has relatively stable fees
    // These are typical values in lovelace
    return {
      slow: '170000',   // ~0.17 ADA
      medium: '200000', // ~0.20 ADA
      fast: '250000'    // ~0.25 ADA
    };
  }

  /**
   * Convert hex to string
   */
  private hexToString(hex: string): string | null {
    try {
      return Buffer.from(hex, 'hex').toString('utf8');
    } catch {
      return null;
    }
  }

  /**
   * Get latest block/slot for TTL calculation
   */
  async getLatestBlock(): Promise<{ slot: number; height: number }> {
    try {
      const headers = this.config.apiKey 
        ? { 'project_id': this.config.apiKey }
        : {};

      const response = await axios.get(
        `${this.baseURL}/blocks/latest`,
        { headers }
      );

      return {
        slot: response.data.slot,
        height: response.data.height
      };
    } catch (error: any) {
      throw new Error(`Failed to fetch latest block: ${error.message}`);
    }
  }
}
