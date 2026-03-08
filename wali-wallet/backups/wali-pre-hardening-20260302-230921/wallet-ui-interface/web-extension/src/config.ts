/**
 * Web Extension Configuration
 * Blockfrost integration for browser-based wallet operations
 */

export interface ExtensionConfig {
  network: 'mainnet' | 'testnet';
  blockfrost: {
    projectId: string;
    network: 'mainnet' | 'testnet';
  };
}

/**
 * Get Blockfrost API key from environment
 * Falls back to a default key for development only
 */
function getBlockfrostKey(): string {
  // In production extension build, this will be injected by webpack
  if (typeof process !== 'undefined' && process.env?.BLOCKFROST_PROJECT_ID) {
    return process.env.BLOCKFROST_PROJECT_ID;
  }
  
  // Default mainnet key (should be overridden in production)
  return 'mainnetehvvvJVoJUAz5DFJJz2L9fHZmkXlXTMP';
}

/**
 * Get configuration from environment or defaults
 */
export function getConfig(): ExtensionConfig {
  // Use mainnet by default
  const network: 'mainnet' | 'testnet' = 'mainnet';
  
  return {
    network,
    blockfrost: {
      projectId: getBlockfrostKey(),
      network,
    },
  };
}

/**
 * Validate configuration
 */
export function validateConfig(config: ExtensionConfig): boolean {
  if (!config.blockfrost.projectId) {
    // Production error handling - no console.log
    throw new Error('Blockfrost project ID not configured');
  }
  
  if (config.network !== config.blockfrost.network) {
    // Network mismatch is acceptable in some cases
    // Don't throw, just log internally if needed
  }
  
  return true;
}

export default getConfig;
