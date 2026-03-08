/**
 * AdDisplay Component
 * Renders advertisements in a non-intrusive, user-friendly manner
 */

import React, { useState } from 'react';
import { Advertisement, AdPlacement } from '../../../../src/monetization/types';

export interface AdDisplayProps {
  ad: Advertisement;
  placement: AdPlacement;
  onImpression?: (adId: string) => void;
  onClick?: (adId: string, targetUrl: string) => void;
  onClose?: () => void;
  
  // Customization
  compact?: boolean;
  showSponsoredLabel?: boolean;
}

/**
 * AdDisplay Component
 */
export const AdDisplay: React.FC<AdDisplayProps> = ({
  ad,
  placement,
  onImpression,
  onClick,
  onClose,
  compact = false,
  showSponsoredLabel = true,
}) => {
  const [isVisible, setIsVisible] = useState(true);
  
  // Track impression on mount
  React.useEffect(() => {
    if (onImpression) {
      onImpression(ad.adId);
    }
  }, [ad.adId, onImpression]);
  
  const handleClick = () => {
    if (onClick) {
      onClick(ad.adId, ad.content.targetUrl);
    }
    // Open in new tab
    window.open(ad.content.targetUrl, '_blank', 'noopener,noreferrer');
  };
  
  const handleClose = () => {
    setIsVisible(false);
    if (onClose) {
      onClose();
    }
  };
  
  if (!isVisible) return null;
  
  // Banner ad
  if (ad.type === 'banner') {
    return (
      <div
        className={`ad-banner ${compact ? 'ad-banner--compact' : ''}`}
        data-placement={placement}
      >
        {showSponsoredLabel && (
          <div className="ad-banner__label">Sponsored</div>
        )}
        
        <div className="ad-banner__content" onClick={handleClick}>
          {ad.content.imageUrl && (
            <img
              src={ad.content.imageUrl}
              alt={ad.content.title}
              className="ad-banner__image"
            />
          )}
          
          <div className="ad-banner__text">
            <h4 className="ad-banner__title">{ad.content.title}</h4>
            {!compact && (
              <p className="ad-banner__description">{ad.content.description}</p>
            )}
            {ad.content.callToAction && (
              <button className="ad-banner__cta">{ad.content.callToAction}</button>
            )}
          </div>
        </div>
        
        <button
          className="ad-banner__close"
          onClick={handleClose}
          aria-label="Close ad"
        >
          ×
        </button>
      </div>
    );
  }
  
  // Native ad (blends with content)
  if (ad.type === 'native') {
    return (
      <div className="ad-native" data-placement={placement}>
        {showSponsoredLabel && (
          <span className="ad-native__label">Sponsored</span>
        )}
        
        <div className="ad-native__content" onClick={handleClick}>
          {ad.content.sponsorLogo && (
            <img
              src={ad.content.sponsorLogo}
              alt={ad.content.sponsorName}
              className="ad-native__logo"
            />
          )}
          
          <div className="ad-native__text">
            <h4 className="ad-native__title">{ad.content.title}</h4>
            <p className="ad-native__description">{ad.content.description}</p>
            {ad.content.sponsorName && (
              <span className="ad-native__sponsor">by {ad.content.sponsorName}</span>
            )}
          </div>
          
          {ad.content.callToAction && (
            <span className="ad-native__cta">{ad.content.callToAction} →</span>
          )}
        </div>
      </div>
    );
  }
  
  // Sponsored content (appears in lists)
  if (ad.type === 'sponsored') {
    return (
      <div className="ad-sponsored" data-placement={placement} onClick={handleClick}>
        <div className="ad-sponsored__header">
          {ad.content.sponsorLogo && (
            <img
              src={ad.content.sponsorLogo}
              alt={ad.content.sponsorName}
              className="ad-sponsored__logo"
            />
          )}
          <div className="ad-sponsored__meta">
            <span className="ad-sponsored__name">{ad.content.sponsorName}</span>
            {showSponsoredLabel && (
              <span className="ad-sponsored__label">• Sponsored</span>
            )}
          </div>
        </div>
        
        <div className="ad-sponsored__content">
          <h4 className="ad-sponsored__title">{ad.content.title}</h4>
          <p className="ad-sponsored__description">{ad.content.description}</p>
        </div>
        
        {ad.content.imageUrl && (
          <img
            src={ad.content.imageUrl}
            alt={ad.content.title}
            className="ad-sponsored__image"
          />
        )}
        
        {ad.content.callToAction && (
          <button className="ad-sponsored__cta">{ad.content.callToAction}</button>
        )}
      </div>
    );
  }
  
  return null;
};

/**
 * Ad Placeholder - shown when no ads available
 */
export const AdPlaceholder: React.FC<{
  placement: AdPlacement;
  message?: string;
}> = ({ placement, message = 'Advertisement space' }) => {
  return (
    <div className="ad-placeholder" data-placement={placement}>
      <span className="ad-placeholder__message">{message}</span>
    </div>
  );
};

export default AdDisplay;
