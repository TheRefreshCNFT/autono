/**
 * PaymentModal Component
 * Handles payment flow for dApp subscriptions and ad purchases
 */

import React, { useState } from 'react';
import { PaymentIntent } from '../../../../src/monetization/payment-processor';

export interface PaymentModalProps {
  intent: PaymentIntent;
  onComplete?: (txHash: string) => void;
  onCancel?: () => void;
  
  // Cardano wallet integration
  walletConnected?: boolean;
  walletAddress?: string;
  onConnectWallet?: () => void;
  onSendPayment?: (amount: string, address: string) => Promise<string>;
}

type PaymentMethod = 'cardano' | 'stripe' | null;
type PaymentStep = 'method' | 'cardano-payment' | 'stripe-payment' | 'confirming' | 'complete';

/**
 * PaymentModal Component
 */
export const PaymentModal: React.FC<PaymentModalProps> = ({
  intent,
  onComplete,
  onCancel,
  walletConnected = false,
  walletAddress,
  onConnectWallet,
  onSendPayment,
}) => {
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>(null);
  const [step, setStep] = useState<PaymentStep>('method');
  const [txHash, setTxHash] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState(false);
  
  const adaAmount = intent.currency === 'ADA'
    ? intent.amount
    : intent.amount * 2; // Simplified conversion (should use real rate)
  
  const lovelaceAmount = intent.expectedAmount || Math.floor(adaAmount * 1_000_000).toString();
  
  const handleSelectMethod = (method: PaymentMethod) => {
    setPaymentMethod(method);
    
    if (method === 'cardano') {
      if (walletConnected) {
        setStep('cardano-payment');
      } else {
        // Prompt to connect wallet first
        setStep('cardano-payment');
      }
    } else if (method === 'stripe') {
      setStep('stripe-payment');
    }
  };
  
  const handleCardanoPayment = async () => {
    if (!walletConnected || !onConnectWallet) {
      setError('Please connect your wallet first');
      return;
    }
    
    if (!onSendPayment || !intent.cardanoPaymentAddress) {
      setError('Payment handler not available');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      const hash = await onSendPayment(lovelaceAmount, intent.cardanoPaymentAddress);
      setTxHash(hash);
      setStep('confirming');
      
      // Simulate confirmation wait (in real app, would poll blockchain)
      setTimeout(() => {
        setStep('complete');
        if (onComplete) {
          onComplete(hash);
        }
      }, 3000);
    } catch (err: any) {
      setError(err.message || 'Payment failed');
    } finally {
      setLoading(false);
    }
  };
  
  const handleStripePayment = async () => {
    setLoading(true);
    setError('');
    
    try {
      // In real implementation, would integrate Stripe checkout
      // For now, just simulate
      setTimeout(() => {
        setStep('complete');
        if (onComplete) {
          onComplete('stripe_' + Math.random().toString(36).substring(7));
        }
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Payment failed');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="payment-modal">
      <div className="payment-modal__overlay" onClick={onCancel} />
      
      <div className="payment-modal__content">
        {/* Header */}
        <div className="payment-modal__header">
          <h2>Complete Payment</h2>
          <button className="payment-modal__close" onClick={onCancel}>×</button>
        </div>
        
        {/* Amount */}
        <div className="payment-modal__amount">
          <div className="amount-display">
            <span className="amount-display__value">
              {intent.currency === 'USD' ? '$' : '₳'}
              {intent.amount.toLocaleString()}
            </span>
            {intent.currency === 'USD' && (
              <span className="amount-display__alt">
                ≈ ₳{adaAmount.toFixed(2)}
              </span>
            )}
          </div>
          {intent.description && (
            <p className="payment-modal__description">{intent.description}</p>
          )}
        </div>
        
        {/* Payment Method Selection */}
        {step === 'method' && (
          <div className="payment-modal__methods">
            <h3>Choose Payment Method</h3>
            
            <button
              className="payment-method payment-method--cardano"
              onClick={() => handleSelectMethod('cardano')}
            >
              <div className="payment-method__icon">₳</div>
              <div className="payment-method__info">
                <h4>Pay with Cardano</h4>
                <p>Fast, secure, and decentralized</p>
              </div>
              <div className="payment-method__badge">Recommended</div>
            </button>
            
            <button
              className="payment-method payment-method--stripe"
              onClick={() => handleSelectMethod('stripe')}
            >
              <div className="payment-method__icon">💳</div>
              <div className="payment-method__info">
                <h4>Pay with Credit Card</h4>
                <p>Visa, Mastercard, Amex</p>
              </div>
            </button>
          </div>
        )}
        
        {/* Cardano Payment */}
        {step === 'cardano-payment' && (
          <div className="payment-modal__cardano">
            <h3>Pay with Cardano</h3>
            
            {!walletConnected ? (
              <div className="wallet-connect">
                <p>Connect your Cardano wallet to continue</p>
                <button
                  className="btn btn--primary"
                  onClick={onConnectWallet}
                >
                  Connect Wallet
                </button>
              </div>
            ) : (
              <div className="payment-details">
                <div className="payment-field">
                  <label>Send to:</label>
                  <code className="payment-address">
                    {intent.cardanoPaymentAddress}
                  </code>
                  <button className="btn btn--small">Copy</button>
                </div>
                
                <div className="payment-field">
                  <label>Amount:</label>
                  <div className="payment-amount">
                    <strong>₳{adaAmount.toFixed(6)}</strong>
                    <span className="payment-amount__lovelace">
                      ({(parseInt(lovelaceAmount) / 1_000_000).toFixed(6)} ADA)
                    </span>
                  </div>
                </div>
                
                <div className="payment-field">
                  <label>From:</label>
                  <code className="payment-address">{walletAddress}</code>
                </div>
                
                {error && (
                  <div className="payment-error">{error}</div>
                )}
                
                <div className="payment-actions">
                  <button
                    className="btn btn--primary btn--large"
                    onClick={handleCardanoPayment}
                    disabled={loading}
                  >
                    {loading ? 'Sending...' : 'Send Payment'}
                  </button>
                  <button className="btn btn--text" onClick={() => setStep('method')}>
                    Back
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Stripe Payment */}
        {step === 'stripe-payment' && (
          <div className="payment-modal__stripe">
            <h3>Pay with Credit Card</h3>
            
            {/* In real implementation, embed Stripe Elements here */}
            <div className="stripe-placeholder">
              <p>Stripe integration would go here</p>
              
              <button
                className="btn btn--primary btn--large"
                onClick={handleStripePayment}
                disabled={loading}
              >
                {loading ? 'Processing...' : 'Pay Now'}
              </button>
              
              <button className="btn btn--text" onClick={() => setStep('method')}>
                Back
              </button>
            </div>
          </div>
        )}
        
        {/* Confirming */}
        {step === 'confirming' && (
          <div className="payment-modal__confirming">
            <div className="loading-spinner" />
            <h3>Confirming Transaction</h3>
            <p>Waiting for blockchain confirmations...</p>
            
            {txHash && (
              <div className="tx-hash">
                <label>Transaction Hash:</label>
                <code>{txHash.substring(0, 16)}...{txHash.substring(txHash.length - 16)}</code>
              </div>
            )}
          </div>
        )}
        
        {/* Complete */}
        {step === 'complete' && (
          <div className="payment-modal__complete">
            <div className="success-icon">✓</div>
            <h3>Payment Successful!</h3>
            <p>Your subscription is now active.</p>
            
            {txHash && (
              <div className="tx-hash">
                <label>Transaction Hash:</label>
                <code>{txHash}</code>
                <button className="btn btn--small">View on Explorer</button>
              </div>
            )}
            
            <button
              className="btn btn--primary btn--large"
              onClick={() => onComplete && onComplete(txHash)}
            >
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default PaymentModal;
