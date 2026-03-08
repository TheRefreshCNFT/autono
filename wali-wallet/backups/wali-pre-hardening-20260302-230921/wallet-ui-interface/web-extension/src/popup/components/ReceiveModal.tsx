/**
 * Multi-chain receive modal component
 * Shows BTC | CARDANO | MIDNIGHT address tabs with QR codes
 */

import React, { useState } from 'react';
import { WalletAddresses } from '../../wallet-bridge';
import './ReceiveModal.css';

interface ReceiveModalProps {
  addresses: WalletAddresses;
  onClose: () => void;
}

type Chain = 'bitcoin' | 'cardano' | 'midnight';

export const ReceiveModal: React.FC<ReceiveModalProps> = ({ addresses, onClose }) => {
  const [activeChain, setActiveChain] = useState<Chain>('cardano');
  const [copiedAddress, setCopiedAddress] = useState<string | null>(null);

  const getCurrentAddress = (): string => {
    switch (activeChain) {
      case 'cardano':
        return addresses.cardano || '';
      case 'bitcoin':
        return addresses.bitcoin?.segwit || ''; // Default to SegWit
      case 'midnight':
        return addresses.night || '';
      default:
        return '';
    }
  };

  const getChainDisplayName = (): string => {
    switch (activeChain) {
      case 'cardano':
        return 'Cardano (ADA)';
      case 'bitcoin':
        return 'Bitcoin (BTC)';
      case 'midnight':
        return 'Midnight';
      default:
        return '';
    }
  };

  const handleCopyAddress = async () => {
    const address = getCurrentAddress();
    try {
      await navigator.clipboard.writeText(address);
      setCopiedAddress(address);
      setTimeout(() => setCopiedAddress(null), 2000);
    } catch (err) {
      console.error('Failed to copy address:', err);
    }
  };

  const generateQRCodeURL = (address: string): string => {
    // Use a QR code generation service (or implement locally)
    return `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(address)}`;
  };

  return (
    <div className="receive-modal-overlay" onClick={onClose}>
      <div className="receive-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>🦭 Receive Crypto</h2>
          <button className="close-btn" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        {/* Chain Tabs */}
        <div className="chain-tabs" role="tablist">
          <button
            role="tab"
            aria-selected={activeChain === 'bitcoin'}
            className={`chain-tab ${activeChain === 'bitcoin' ? 'active' : ''}`}
            onClick={() => setActiveChain('bitcoin')}
          >
            ₿ BTC
          </button>
          <button
            role="tab"
            aria-selected={activeChain === 'cardano'}
            className={`chain-tab ${activeChain === 'cardano' ? 'active' : ''}`}
            onClick={() => setActiveChain('cardano')}
          >
            ₳ CARDANO
          </button>
          <button
            role="tab"
            aria-selected={activeChain === 'midnight'}
            className={`chain-tab ${activeChain === 'midnight' ? 'active' : ''}`}
            onClick={() => setActiveChain('midnight')}
          >
            🌙 MIDNIGHT
          </button>
        </div>

        {/* Address Display */}
        <div className="address-content" role="tabpanel">
          <div className="chain-name">{getChainDisplayName()}</div>

          {/* QR Code */}
          <div className="qr-code-container">
            <img
              src={generateQRCodeURL(getCurrentAddress())}
              alt={`QR code for ${getChainDisplayName()} address`}
              className="qr-code"
            />
          </div>

          {/* Address Text */}
          <div className="address-display">
            <code className="address-text">{getCurrentAddress()}</code>
          </div>

          {/* Bitcoin Address Type Selector */}
          {activeChain === 'bitcoin' && addresses.bitcoin && (
            <div className="btc-address-types">
              <p className="address-type-label">Address Type:</p>
              <div className="address-type-options">
                <label className="address-type-option">
                  <input
                    type="radio"
                    name="btc-type"
                    defaultChecked
                    onChange={() => {/* SegWit is default */}}
                  />
                  <span>
                    <strong>SegWit</strong> (Recommended)
                    <br />
                    <code className="small-address">{addresses.bitcoin.segwit}</code>
                  </span>
                </label>
                <label className="address-type-option">
                  <input
                    type="radio"
                    name="btc-type"
                    onChange={() => {/* Switch to legacy */}}
                  />
                  <span>
                    <strong>Legacy</strong> (Compatible)
                    <br />
                    <code className="small-address">{addresses.bitcoin.legacy}</code>
                  </span>
                </label>
                <label className="address-type-option">
                  <input
                    type="radio"
                    name="btc-type"
                    onChange={() => {/* Switch to taproot */}}
                  />
                  <span>
                    <strong>Taproot</strong> (Advanced)
                    <br />
                    <code className="small-address">{addresses.bitcoin.taproot}</code>
                  </span>
                </label>
              </div>
            </div>
          )}

          {/* Copy Button */}
          <button
            className="copy-btn"
            onClick={handleCopyAddress}
            disabled={copiedAddress === getCurrentAddress()}
          >
            {copiedAddress === getCurrentAddress() ? '✅ Copied!' : '📋 Copy Address'}
          </button>

          {/* Help Text */}
          <p className="help-text">
            {activeChain === 'cardano' && 'Send ADA or Cardano tokens to this address'}
            {activeChain === 'bitcoin' && 'Send Bitcoin (BTC) to this address'}
            {activeChain === 'midnight' && 'Send Midnight tokens to this address'}
          </p>
        </div>
      </div>
    </div>
  );
};
