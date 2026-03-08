/**
 * Injected script providing window.cardano API
 * Runs in page context to allow dApp interaction
 */

interface CardanoAPI {
  enable(): Promise<CardanoWallet>;
  isEnabled(): Promise<boolean>;
  apiVersion: string;
  name: string;
  icon: string;
}

interface CardanoWallet {
  getBalance(): Promise<string>;
  getUsedAddresses(): Promise<string[]>;
  getUnusedAddresses(): Promise<string[]>;
  getChangeAddress(): Promise<string>;
  signTx(tx: string): Promise<string>;
  signData(address: string, payload: string): Promise<{ signature: string; key: string }>;
  submitTx(tx: string): Promise<string>;
}

class ConversationalWalletAPI implements CardanoAPI {
  apiVersion = '0.1.0';
  name = 'wAli';
  icon = 'data:image/svg+xml;base64,...'; // Add base64 icon

  private enabled = false;

  async enable(): Promise<CardanoWallet> {
    if (this.enabled) {
      return this.getWalletAPI();
    }

    // Request connection approval
    const approved = await this.requestConnection();
    
    if (!approved) {
      throw new Error('User declined connection');
    }

    this.enabled = true;
    return this.getWalletAPI();
  }

  async isEnabled(): Promise<boolean> {
    return this.enabled;
  }

  private async requestConnection(): Promise<boolean> {
    return new Promise((resolve) => {
      const requestId = Date.now().toString();

      window.postMessage({
        type: 'DAPP_CONNECT_REQUEST',
        data: {
          dappId: window.location.hostname,
          dappName: document.title || window.location.hostname,
          dappUrl: window.location.href,
          requestedPermissions: [
            { type: 'read_balance', description: 'Read wallet balance', required: true },
            { type: 'read_address', description: 'Read wallet addresses', required: true },
            { type: 'sign_transaction', description: 'Sign transactions', required: true },
          ],
          requestId,
        },
      }, '*');

      const listener = (event: MessageEvent) => {
        if (event.data.type === 'DAPP_CONNECT_RESPONSE') {
          window.removeEventListener('message', listener);
          resolve(event.data.approved);
        }
      };

      window.addEventListener('message', listener);

      // Timeout after 2 minutes
      setTimeout(() => {
        window.removeEventListener('message', listener);
        resolve(false);
      }, 120000);
    });
  }

  private getWalletAPI(): CardanoWallet {
    return {
      getBalance: async () => {
        // Beta: dApp integration coming in next release
        throw new Error('dApp integration not available in beta. Coming soon!');
      },

      getUsedAddresses: async () => {
        // Beta: dApp integration coming in next release
        throw new Error('dApp integration not available in beta. Coming soon!');
      },

      getUnusedAddresses: async () => {
        // Beta: dApp integration coming in next release
        throw new Error('dApp integration not available in beta. Coming soon!');
      },

      getChangeAddress: async () => {
        // Beta: dApp integration coming in next release
        throw new Error('dApp integration not available in beta. Coming soon!');
      },

      signTx: async (tx: string) => {
        return new Promise((resolve, reject) => {
          const requestId = Date.now().toString();

          window.postMessage({
            type: 'DAPP_TRANSACTION_REQUEST',
            data: {
              tx,
              requestId,
            },
          }, '*');

          const listener = (event: MessageEvent) => {
            if (
              event.data.type === 'DAPP_TRANSACTION_RESPONSE' &&
              event.data.requestId === requestId
            ) {
              window.removeEventListener('message', listener);
              if (event.data.approved) {
                resolve(event.data.signedTx);
              } else {
                reject(new Error('User declined transaction'));
              }
            }
          };

          window.addEventListener('message', listener);
        });
      },

      signData: async (address: string, payload: string) => {
        // Beta: dApp integration coming in next release
        throw new Error('dApp integration not available in beta. Coming soon!');
      },

      submitTx: async (tx: string) => {
        // Beta: dApp integration coming in next release
        throw new Error('dApp integration not available in beta. Coming soon!');
      },
    };
  }
}

// Inject API into window
if (typeof window !== 'undefined') {
  (window as any).cardano = (window as any).cardano || {};
  (window as any).cardano.conversationalwallet = new ConversationalWalletAPI();
}
