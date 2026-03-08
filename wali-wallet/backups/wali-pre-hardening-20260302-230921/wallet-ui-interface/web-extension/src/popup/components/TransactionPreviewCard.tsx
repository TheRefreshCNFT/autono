import React from 'react';
import { TransactionPreview, formatAssetAmount } from '@wallet-ui/shared';
import './TransactionPreviewCard.css';

interface TransactionPreviewCardProps {
  preview: TransactionPreview;
  onConfirm: () => void;
  onEdit: () => void;
  onCancel: () => void;
}

export const TransactionPreviewCard: React.FC<TransactionPreviewCardProps> = ({
  preview,
  onConfirm,
  onEdit,
  onCancel,
}) => {
  return (
    <div className="transaction-preview-card" role="region" aria-label="Transaction preview">
      {/* Human-readable description */}
      <div className="preview-description">
        {preview.humanReadable}
      </div>

      {/* Warnings */}
      {preview.warnings.length > 0 && (
        <div className="preview-warnings" role="alert" aria-live="assertive">
          {preview.warnings.map((warning: string, idx: number) => (
            <div key={idx} className="warning-item">
              ⚠️ {warning}
            </div>
          ))}
        </div>
      )}

      {/* Fee breakdown */}
      <div className="preview-details">
        <div className="detail-row">
          <span className="detail-label">Network Fee:</span>
          <span className="detail-value">
            {formatAssetAmount(preview.fee, preview.feeAsset.decimals)} {preview.feeAsset.symbol}
          </span>
        </div>
        {preview.intent.amount && preview.intent.asset && (
          <div className="detail-row total-row">
            <span className="detail-label">Total Cost:</span>
            <span className="detail-value">
              {formatAssetAmount(preview.totalCost, preview.intent.asset.decimals)} {preview.intent.asset.symbol}
            </span>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="preview-actions" role="toolbar" aria-label="Transaction actions">
        <button
          onClick={onCancel}
          className="action-btn cancel-btn"
          aria-label="Cancel transaction"
        >
          ✕ Cancel
        </button>
        <button
          onClick={onEdit}
          className="action-btn edit-btn"
          aria-label="Edit transaction"
        >
          ✎ Edit
        </button>
        <button
          onClick={onConfirm}
          className="action-btn confirm-btn"
          aria-label="Confirm and send transaction"
        >
          ✓ Send
        </button>
      </div>
    </div>
  );
};
