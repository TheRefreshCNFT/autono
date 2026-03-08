import React from 'react';
import { View, TouchableOpacity, Text, StyleSheet } from 'react-native';

interface QuickActionsProps {
  onAction: (command: string) => void;
  disabled?: boolean;
}

export const QuickActions: React.FC<QuickActionsProps> = ({ onAction, disabled }) => {
  const actions = [
    { emoji: '💰', label: 'Balance', command: 'show balance' },
    { emoji: '📜', label: 'History', command: 'show transactions' },
    { emoji: '⬇️', label: 'Receive', command: 'receive' },
  ];

  return (
    <View style={styles.container}>
      {actions.map(action => (
        <TouchableOpacity
          key={action.label}
          style={[styles.button, disabled && styles.buttonDisabled]}
          onPress={() => onAction(action.command)}
          disabled={disabled}
          accessible={true}
          accessibilityLabel={action.label}
          accessibilityRole="button"
        >
          <Text style={styles.emoji}>{action.emoji}</Text>
          <Text style={styles.label}>{action.label}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderTopColor: '#e1e8ed',
    gap: 8,
  },
  button: {
    flex: 1,
    padding: 12,
    borderWidth: 1,
    borderColor: '#e1e8ed',
    borderRadius: 8,
    alignItems: 'center',
    backgroundColor: 'white',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  emoji: {
    fontSize: 20,
    marginBottom: 4,
  },
  label: {
    fontSize: 12,
    color: '#4a5568',
    fontWeight: '500',
  },
});
