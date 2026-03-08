/**
 * DAppConnector Component
 * UI for connecting paid dApp integrations
 */

import React, { useState } from 'react';
import { DAppIntegration, DAppTier, TierDefinition } from '../../../../src/monetization/types';

export interface DAppConnectorProps {
  dapp?: DAppIntegration;
  tiers: TierDefinition[];
  onConnect?: (tier: DAppTier) => void;
  onUpgrade?: (newTier: DAppTier) => void;
  onDisconnect?: () => void;
}

/**
 * DAppConnector Component
 */
export const DAppConnector: React.FC<DAppConnectorProps> = ({
  dapp,
  tiers,
  onConnect,
  onUpgrade,
  onDisconnect,
}) => {
  const [selectedTier, setSelectedTier] = useState<DAppTier>('basic');
  const [showPayment, setShowPayment] = useState(false);
  
  const isConnected = !!dapp;
  const isPaid = dapp?.paymentStatus === 'paid';
  const isExpired = dapp?.paymentStatus === 'expired';
  const isTrial = dapp?.paymentStatus === 'trial';
  
  const handleConnect = () => {
    if (onConnect) {
      onConnect(selectedTier);
    }
  };
  
  const handleUpgrade = (tier: DAppTier) => {
    if (onUpgrade) {
      onUpgrade(tier);
    }
  };
  
  // Not connected - show tier selection
  if (!isConnected) {
    return (
      <div className="dapp-connector">
        <div className="dapp-connector__header">
          <h2>Connect Your dApp to wAli</h2>
          <p>Choose a plan and start integrating with wAli's wallet infrastructure</p>
        </div>
        
        <div className="dapp-connector__tiers">
          {tiers.map((tier) => (
            <div
              key={tier.tier}
              className={`tier-card ${selectedTier === tier.tier ? 'tier-card--selected' : ''}`}
              onClick={() => setSelectedTier(tier.tier)}
            >
              <div className="tier-card__header">
                <h3>{tier.name}</h3>
                {tier.monthlyPrice > 0 ? (
                  <div className="tier-card__price">
                    <span className="tier-card__amount">${tier.monthlyPrice}</span>
                    <span className="tier-card__period">/month</span>
                  </div>
                ) : (
                  <div className="tier-card__price">
                    <span className="tier-card__custom">Custom Pricing</span>
                  </div>
                )}
              </div>
              
              <div className="tier-card__features">
                <div className="tier-card__limit">
                  {tier.maxUsers === -1 ? 'Unlimited users' : `Up to ${tier.maxUsers.toLocaleString()} users`}
                </div>
                
                <ul>
                  {tier.features.map((feature, i) => (
                    <li key={i}>✓ {feature}</li>
                  ))}
                </ul>
              </div>
              
              <div className="tier-card__support">
                <span>Support: {tier.support}</span>
              </div>
            </div>
          ))}
        </div>
        
        <div className="dapp-connector__actions">
          <button
            className="btn btn--primary btn--large"
            onClick={handleConnect}
          >
            Start with {tiers.find(t => t.tier === selectedTier)?.name} Plan
          </button>
          
          <p className="dapp-connector__trial-notice">
            🎉 Start with a 14-day free trial
          </p>
        </div>
      </div>
    );
  }
  
  // Connected - show current status
  return (
    <div className="dapp-status">
      <div className="dapp-status__header">
        <h2>{dapp.name}</h2>
        <div className={`dapp-status__badge dapp-status__badge--${dapp.paymentStatus}`}>
          {dapp.paymentStatus === 'trial' && '🎁 Trial'}
          {dapp.paymentStatus === 'paid' && '✓ Active'}
          {dapp.paymentStatus === 'expired' && '⚠️ Expired'}
        </div>
      </div>
      
      <div className="dapp-status__info">
        <div className="dapp-status__tier">
          <strong>Plan:</strong> {tiers.find(t => t.tier === dapp.tier)?.name}
          <span className="dapp-status__price">${dapp.monthlyFee}/month</span>
        </div>
        
        <div className="dapp-status__usage">
          <div className="usage-bar">
            <div className="usage-bar__label">
              <span>Users: {dapp.connectedUsers.toLocaleString()}</span>
              <span>
                {dapp.maxUsers === -1 ? 'Unlimited' : `${dapp.maxUsers.toLocaleString()} max`}
              </span>
            </div>
            
            {dapp.maxUsers !== -1 && (
              <div className="usage-bar__track">
                <div
                  className="usage-bar__fill"
                  style={{ width: `${(dapp.connectedUsers / dapp.maxUsers) * 100}%` }}
                />
              </div>
            )}
          </div>
        </div>
        
        {dapp.expiresAt && (
          <div className="dapp-status__expiry">
            {isTrial && (
              <p>Trial expires in {Math.ceil((dapp.expiresAt - Date.now()) / (24 * 60 * 60 * 1000))} days</p>
            )}
            {isPaid && (
              <p>Next billing: {new Date(dapp.expiresAt).toLocaleDateString()}</p>
            )}
            {isExpired && (
              <p className="dapp-status__warning">
                ⚠️ Subscription expired. Please renew to continue service.
              </p>
            )}
          </div>
        )}
      </div>
      
      <div className="dapp-status__api">
        <h3>API Credentials</h3>
        <div className="api-key">
          <label>API Key:</label>
          <code className="api-key__value">{dapp.apiKey?.substring(0, 20)}...</code>
          <button className="btn btn--small">Copy</button>
        </div>
        
        {dapp.webhookUrl && (
          <div className="webhook">
            <label>Webhook URL:</label>
            <input
              type="text"
              value={dapp.webhookUrl}
              readOnly
              className="webhook__input"
            />
          </div>
        )}
      </div>
      
      <div className="dapp-status__actions">
        {(isTrial || isExpired) && (
          <button className="btn btn--primary" onClick={() => setShowPayment(true)}>
            Upgrade to Paid Plan
          </button>
        )}
        
        {isPaid && dapp.tier !== 'enterprise' && (
          <button
            className="btn btn--secondary"
            onClick={() => handleUpgrade('enterprise')}
          >
            Upgrade to Enterprise
          </button>
        )}
        
        <button className="btn btn--danger" onClick={onDisconnect}>
          Disconnect dApp
        </button>
      </div>
      
      {showPayment && (
        <div className="payment-modal">
          <div className="payment-modal__overlay" onClick={() => setShowPayment(false)} />
          <div className="payment-modal__content">
            <h3>Complete Payment</h3>
            <p>Choose your payment method to activate your subscription</p>
            
            <div className="payment-options">
              <button className="payment-option payment-option--cardano">
                <span className="payment-option__icon">₳</span>
                <span className="payment-option__label">Pay with Cardano</span>
                <span className="payment-option__badge">Recommended</span>
              </button>
              
              <button className="payment-option payment-option--stripe">
                <span className="payment-option__icon">💳</span>
                <span className="payment-option__label">Pay with Card (Stripe)</span>
              </button>
            </div>
            
            <button className="btn btn--text" onClick={() => setShowPayment(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DAppConnector;
