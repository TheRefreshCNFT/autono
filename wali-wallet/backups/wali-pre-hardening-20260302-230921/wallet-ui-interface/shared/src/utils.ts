/**
 * Utility functions for wallet UI
 */

import { Asset, Chain } from './types';

/**
 * Format asset amount with proper decimals
 */
export function formatAssetAmount(amount: string, decimals: number): string {
  const num = parseFloat(amount);
  if (isNaN(num)) return '0';
  
  return num.toFixed(decimals).replace(/\.?0+$/, '');
}

/**
 * Format large numbers with appropriate suffixes (K, M, B)
 */
export function formatLargeNumber(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  
  if (num >= 1e9) return `${(num / 1e9).toFixed(2)}B`;
  if (num >= 1e6) return `${(num / 1e6).toFixed(2)}M`;
  if (num >= 1e3) return `${(num / 1e3).toFixed(2)}K`;
  
  return num.toFixed(2);
}

/**
 * Validate address format
 */
export function isValidAddress(address: string, chain: Chain): boolean {
  if (chain === 'cardano') {
    return /^addr1[a-z0-9]{58,}$/i.test(address);
  } else if (chain === 'bitcoin') {
    return /^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,87}$/.test(address);
  }
  return false;
}

/**
 * Validate handle format
 */
export function isValidHandle(handle: string): boolean {
  return /^\$[\w-]+$/.test(handle);
}

/**
 * Generate accessible color for asset badges
 */
export function getAssetColor(symbol: string): string {
  const colors: Record<string, string> = {
    'ADA': '#0033AD',
    'BTC': '#F7931A',
    'USDT': '#26A17B',
    'USDC': '#2775CA',
  };
  
  return colors[symbol] || '#666666';
}

/**
 * Sort assets by value (native first, then by balance)
 */
export function sortAssets(assets: Asset[]): Asset[] {
  return [...assets].sort((a, b) => {
    // Native assets first
    if (a.type === 'native' && b.type !== 'native') return -1;
    if (a.type !== 'native' && b.type === 'native') return 1;
    
    // Then by balance
    const aBalance = parseFloat(a.balance);
    const bBalance = parseFloat(b.balance);
    return bBalance - aBalance;
  });
}

/**
 * Generate error message with recovery action
 */
export function generateErrorMessage(error: any): { message: string; recoveryAction?: string } {
  if (error.code === 'INSUFFICIENT_FUNDS') {
    return {
      message: 'You don\'t have enough funds for this transaction',
      recoveryAction: 'Add more funds to your wallet or reduce the amount',
    };
  }
  
  if (error.code === 'INVALID_ADDRESS') {
    return {
      message: 'The recipient address is invalid',
      recoveryAction: 'Double-check the address and try again',
    };
  }
  
  if (error.code === 'NETWORK_ERROR') {
    return {
      message: 'Unable to connect to the blockchain network',
      recoveryAction: 'Check your internet connection and try again',
    };
  }
  
  return {
    message: error.message || 'An unexpected error occurred',
    recoveryAction: 'Please try again or contact support if the problem persists',
  };
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 3)}...`;
}

/**
 * Debounce function for search/input handlers
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  waitMs: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;
  
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), waitMs);
  };
}

/**
 * Format timestamp to relative time
 */
export function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;
  
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
  if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
  return 'Just now';
}
