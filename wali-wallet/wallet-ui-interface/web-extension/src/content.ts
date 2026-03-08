/**
 * Content script injected into web pages
 * Provides window.cardano API for dApp integration
 */

// Inject the provider script into the page context
const script = document.createElement('script');
script.src = chrome.runtime.getURL('injected.js');
script.onload = function() {
  script.remove();
};
(document.head || document.documentElement).appendChild(script);

// Listen for messages from injected script
window.addEventListener('message', (event) => {
  if (event.source !== window) return;
  if (!event.data.type) return;

  // Forward to background script
  if (event.data.type.startsWith('DAPP_')) {
    chrome.runtime.sendMessage(event.data);
  }
});

// Listen for responses from background script
chrome.runtime.onMessage.addListener((message) => {
  // Forward to injected script
  window.postMessage(message, '*');
});
