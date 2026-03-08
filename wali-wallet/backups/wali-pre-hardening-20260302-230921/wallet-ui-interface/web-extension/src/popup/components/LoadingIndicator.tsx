import React from 'react';
import './LoadingIndicator.css';

interface LoadingIndicatorProps {
  operation?: string;
}

export const LoadingIndicator: React.FC<LoadingIndicatorProps> = ({ operation }) => {
  return (
    <div className="loading-indicator" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true"></div>
      <span className="loading-text">
        {operation || 'Processing...'}
      </span>
    </div>
  );
};
