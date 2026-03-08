import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { TransactionPreview, formatAssetAmount } from '@wallet-ui/shared';

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
    <View style={styles.container} accessible={true} accessibilityRole="summary">
      {/* Description */}
      <Text style={styles.description}>{preview.humanReadable}</Text>

      {/* Warnings */}
      {preview.warnings.length > 0 && (
        <View style={styles.warningsContainer} accessible={true} accessibilityRole="alert">
          {preview.warnings.map((warning, idx) => (
            <Text key={idx} style={styles.warning}>
              ⚠️ {warning}
            </Text>
          ))}
        </View>
      )}

      {/* Details */}
      <View style={styles.details}>
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Network Fee:</Text>
          <Text style={styles.detailValue}>
            {formatAssetAmount(preview.fee, preview.feeAsset.decimals)} {preview.feeAsset.symbol}
          </Text>
        </View>
        {preview.intent.amount && preview.intent.asset && (
          <View style={[styles.detailRow, styles.totalRow]}>
            <Text style={styles.detailLabel}>Total Cost:</Text>
            <Text style={styles.detailValue}>
              {formatAssetAmount(preview.totalCost, preview.intent.asset.decimals)} {preview.intent.asset.symbol}
            </Text>
          </View>
        )}
      </View>

      {/* Actions */}
      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.button, styles.cancelButton]}
          onPress={onCancel}
          accessible={true}
          accessibilityLabel="Cancel transaction"
          accessibilityRole="button"
        >
          <Text style={styles.cancelButtonText}>✕ Cancel</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, styles.editButton]}
          onPress={onEdit}
          accessible={true}
          accessibilityLabel="Edit transaction"
          accessibilityRole="button"
        >
          <Text style={styles.editButtonText}>✎ Edit</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, styles.confirmButton]}
          onPress={onConfirm}
          accessible={true}
          accessibilityLabel="Confirm and send transaction"
          accessibilityRole="button"
        >
          <Text style={styles.confirmButtonText}>✓ Send</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'white',
    borderWidth: 2,
    borderColor: '#667eea',
    borderRadius: 12,
    padding: 16,
    marginVertical: 12,
    shadowColor: '#667eea',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 4,
  },
  description: {
    fontSize: 14,
    lineHeight: 22,
    color: '#2d3748',
    marginBottom: 16,
  },
  warningsContainer: {
    backgroundColor: '#fff5f5',
    borderLeftWidth: 4,
    borderLeftColor: '#fc8181',
    padding: 12,
    borderRadius: 4,
    marginBottom: 16,
  },
  warning: {
    fontSize: 13,
    color: '#c53030',
    marginBottom: 4,
  },
  details: {
    backgroundColor: '#f7fafc',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 6,
  },
  totalRow: {
    borderTopWidth: 1,
    borderTopColor: '#e1e8ed',
    marginTop: 8,
    paddingTop: 12,
  },
  detailLabel: {
    color: '#718096',
    fontSize: 13,
  },
  detailValue: {
    color: '#2d3748',
    fontSize: 13,
    fontWeight: '500',
  },
  actions: {
    flexDirection: 'row',
    gap: 8,
  },
  button: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  cancelButton: {
    backgroundColor: '#f7fafc',
    borderWidth: 1,
    borderColor: '#e1e8ed',
  },
  editButton: {
    backgroundColor: '#edf2f7',
    borderWidth: 1,
    borderColor: '#cbd5e0',
  },
  confirmButton: {
    backgroundColor: '#48bb78',
  },
  cancelButtonText: {
    color: '#718096',
    fontSize: 13,
    fontWeight: '500',
  },
  editButtonText: {
    color: '#4a5568',
    fontSize: 13,
    fontWeight: '500',
  },
  confirmButtonText: {
    color: 'white',
    fontSize: 13,
    fontWeight: '600',
  },
});
