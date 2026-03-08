/**
 * Background service worker for extension
 * Handles dApp connection requests and wallet-core-engine integration
 */

import { DAppConnectionRequest, DAppConnection } from '@wallet-ui/shared';

// Listen for dApp connection requests from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'DAPP_CONNECT_REQUEST') {
    handleDAppConnectionRequest(request.data, sender.tab?.id);
    sendResponse({ received: true });
  }

  if (request.type === 'DAPP_TRANSACTION_REQUEST') {
    handleDAppTransactionRequest(request.data, sender.tab?.id);
    sendResponse({ received: true });
  }

  return true; // Keep channel open for async response
});

async function handleDAppConnectionRequest(
  connectionRequest: DAppConnectionRequest,
  tabId?: number
) {
  // Show approval popup
  const approved = await showConnectionApprovalDialog(connectionRequest);

  if (approved && tabId) {
    // Store connection
    await storeConnection(connectionRequest);

    // Notify content script
    chrome.tabs.sendMessage(tabId, {
      type: 'DAPP_CONNECT_RESPONSE',
      approved: true,
      permissions: connectionRequest.requestedPermissions,
    });

    // Show notification
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: 'dApp Connected',
      message: `${connectionRequest.dappName} has been connected to your wallet`,
    });
  } else if (tabId) {
    chrome.tabs.sendMessage(tabId, {
      type: 'DAPP_CONNECT_RESPONSE',
      approved: false,
    });
  }
}

async function handleDAppTransactionRequest(data: any, tabId?: number) {
  // Open popup for transaction approval
  chrome.action.openPopup();
  
  // Store pending transaction
  await chrome.storage.local.set({
    pendingTransaction: {
      ...data,
      tabId,
      timestamp: Date.now(),
    },
  });
}

async function showConnectionApprovalDialog(
  request: DAppConnectionRequest
): Promise<boolean> {
  // Store pending request
  await chrome.storage.local.set({
    pendingConnection: request,
  });

  // Open popup
  chrome.action.openPopup();

  // Wait for user approval (simplified - would need proper implementation)
  return new Promise((resolve) => {
    const listener = (changes: any, areaName: string) => {
      if (areaName === 'local' && changes.connectionApproval) {
        chrome.storage.onChanged.removeListener(listener);
        resolve(changes.connectionApproval.newValue);
      }
    };
    chrome.storage.onChanged.addListener(listener);
  });
}

async function storeConnection(request: DAppConnectionRequest) {
  const { connections = [] } = await chrome.storage.local.get('connections');

  const newConnection: DAppConnection = {
    dappId: request.dappId,
    dappName: request.dappName,
    dappUrl: request.dappUrl,
    permissions: request.requestedPermissions,
    connectedAt: Date.now(),
    lastUsed: Date.now(),
  };

  connections.push(newConnection);
  await chrome.storage.local.set({ connections });
}

// Initialize extension
chrome.runtime.onInstalled.addListener(() => {
  // wAli Extension installed - production build
});
