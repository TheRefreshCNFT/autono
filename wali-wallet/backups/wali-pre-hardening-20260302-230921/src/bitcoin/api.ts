/**
 * Bitcoin blockchain API interactions (Blockstream or similar)
 */

import axios from 'axios';
import { Balance, Transaction, TransactionInput, TransactionOutput } from '../types';

export interface BitcoinAPIConfig {
  provider: 'blockstream' | 'mempool';
  network: 'mainnet' | 'testnet';
}

export class BitcoinAPI {
  private config: BitcoinAPIConfig;
  private baseURL: string;

  constructor(config: BitcoinAPIConfig) {
    this.config = config;
    
    if (config.provider === 'blockstream') {
      this.baseURL = config.network === 'mainnet'
        ? 'https://blockstream.info/api'
        : 'https://blockstream.info/testnet/api';
    } else {
      this.baseURL = config.network === 'mainnet'
        ? 'https://mempool.space/api'
        : 'https://mempool.space/testnet/api';
    }
  }

  /**
   * Get balance for a Bitcoin address
   */
  async getBalance(address: string): Promise<Balance> {
    try {
      const response = await axios.get(`${this.baseURL}/address/${address}`);
      const data = response.data;

      const chainStats = data.chain_stats || {};
      const mempoolStats = data.mempool_stats || {};

      const funded = BigInt(chainStats.funded_txo_sum || 0);
      const spent = BigInt(chainStats.spent_txo_sum || 0);
      const mempoolFunded = BigInt(mempoolStats.funded_txo_sum || 0);
      const mempoolSpent = BigInt(mempoolStats.spent_txo_sum || 0);

      const balance = funded - spent + mempoolFunded - mempoolSpent;

      return {
        chain: 'bitcoin',
        address,
        native: {
          amount: balance.toString(),
          symbol: 'BTC',
          decimals: 8
        }
      };
    } catch (error: any) {
      throw new Error(`Failed to fetch Bitcoin balance: ${error.message}`);
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
      const response = await axios.get(
        `${this.baseURL}/address/${address}/txs`
      );

      const txs = response.data.slice(0, limit);
      const transactions: Transaction[] = [];

      for (const tx of txs) {
        transactions.push(await this.parseTransaction(tx));
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
      const response = await axios.get(`${this.baseURL}/tx/${txHash}`);
      return await this.parseTransaction(response.data);
    } catch (error: any) {
      throw new Error(`Failed to fetch transaction detail: ${error.message}`);
    }
  }

  /**
   * Parse raw transaction data
   */
  private async parseTransaction(tx: any): Promise<Transaction> {
    const inputs: TransactionInput[] = tx.vin.map((input: any) => ({
      txHash: input.txid,
      index: input.vout,
      amount: input.prevout?.value?.toString() || '0'
    }));

    const outputs: TransactionOutput[] = tx.vout.map((output: any) => ({
      address: output.scriptpubkey_address || 'unknown',
      amount: output.value.toString()
    }));

    return {
      chain: 'bitcoin',
      hash: tx.txid,
      timestamp: tx.status.block_time ? tx.status.block_time * 1000 : Date.now(),
      status: tx.status.confirmed ? 'confirmed' : 'pending',
      inputs,
      outputs,
      fee: tx.fee?.toString() || '0',
      confirmations: tx.status.block_height 
        ? await this.getConfirmations(tx.status.block_height)
        : 0
    };
  }

  /**
   * Get UTXOs for an address
   */
  async getUTXOs(address: string): Promise<Array<{
    txHash: string;
    index: number;
    amount: number;
    script?: string;
  }>> {
    try {
      const response = await axios.get(
        `${this.baseURL}/address/${address}/utxo`
      );

      return response.data.map((utxo: any) => ({
        txHash: utxo.txid,
        index: utxo.vout,
        amount: utxo.value,
        script: utxo.scriptpubkey
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
      const response = await axios.post(
        `${this.baseURL}/tx`,
        signedTxHex,
        {
          headers: { 'Content-Type': 'text/plain' }
        }
      );

      return response.data;
    } catch (error: any) {
      throw new Error(`Failed to submit transaction: ${error.message}`);
    }
  }

  /**
   * Estimate current fee rates
   */
  async estimateFees(): Promise<{
    slow: string;
    medium: string;
    fast: string;
  }> {
    try {
      const response = await axios.get(`${this.baseURL}/fee-estimates`);
      const feeData = response.data;

      // Get fee rates for different confirmation targets
      // Values are in sat/vB
      const slow = Math.ceil(feeData['144'] || 1);    // ~1 day
      const medium = Math.ceil(feeData['6'] || 5);    // ~1 hour
      const fast = Math.ceil(feeData['1'] || 10);     // Next block

      return {
        slow: slow.toString(),
        medium: medium.toString(),
        fast: fast.toString()
      };
    } catch (error: any) {
      // Return default values if API fails
      return {
        slow: '1',
        medium: '5',
        fast: '10'
      };
    }
  }

  /**
   * Get current block height
   */
  async getBlockHeight(): Promise<number> {
    try {
      const response = await axios.get(`${this.baseURL}/blocks/tip/height`);
      return typeof response.data === 'number' 
        ? response.data 
        : parseInt(response.data);
    } catch (error: any) {
      throw new Error(`Failed to fetch block height: ${error.message}`);
    }
  }

  /**
   * Calculate confirmations from block height
   */
  private async getConfirmations(blockHeight: number): Promise<number> {
    try {
      const currentHeight = await this.getBlockHeight();
      return Math.max(0, currentHeight - blockHeight + 1);
    } catch {
      return 0;
    }
  }

  /**
   * Validate address format
   */
  validateAddress(address: string): boolean {
    // Basic Bitcoin address validation
    const mainnetRegex = /^(1|3|bc1)[a-zA-HJ-NP-Z0-9]{25,62}$/;
    const testnetRegex = /^(m|n|2|tb1)[a-zA-HJ-NP-Z0-9]{25,62}$/;

    if (this.config.network === 'mainnet') {
      return mainnetRegex.test(address);
    } else {
      return testnetRegex.test(address);
    }
  }
}
