import React from 'react';
import './ErrorBanner.css';

interface ErrorBannerProps {
  message: string;
  recoveryAction?: string;
  onDismiss: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  message,
  recoveryAction,
  onDismiss,
}) => {
  return (
    <div className="error-banner" role="alert" aria-live="assertive">
      <div className="error-content">
        <span className="error-icon" aria-hidden="true">⚠️</span>
        <div className="error-text">
          <div className="error-message">{message}</div>
          {recoveryAction && (
            <div className="error-recovery">{recoveryAction}</div>
          )}
        </div>
      </div>
      <button
        onClick={onDismiss}
        className="error-dismiss"
        aria-label="Dismiss error"
      >
        ✕
      </button>
    </div>
  );
};
