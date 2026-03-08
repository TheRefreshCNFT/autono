import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';

export const WalletSetupScreen: React.FC = ({ navigation }: any) => {
  const [step, setStep] = useState<'choice' | 'create' | 'restore'>('choice');

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {step === 'choice' && (
        <>
          <Text style={styles.title}>Let's set up your wallet</Text>
          <Text style={styles.subtitle}>
            Choose how you'd like to get started
          </Text>

          <TouchableOpacity
            style={styles.option}
            onPress={() => setStep('create')}
            accessible={true}
            accessibilityLabel="Create new wallet"
            accessibilityRole="button"
          >
            <Text style={styles.optionEmoji}>✨</Text>
            <Text style={styles.optionTitle}>Create New Wallet</Text>
            <Text style={styles.optionDesc}>
              Generate a new wallet with a secure recovery phrase
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.option}
            onPress={() => setStep('restore')}
            accessible={true}
            accessibilityLabel="Restore existing wallet"
            accessibilityRole="button"
          >
            <Text style={styles.optionEmoji}>🔄</Text>
            <Text style={styles.optionTitle}>Restore Existing Wallet</Text>
            <Text style={styles.optionDesc}>
              Use your recovery phrase to restore your wallet
            </Text>
          </TouchableOpacity>
        </>
      )}

      {step === 'create' && (
        <View>
          <Text style={styles.title}>Create New Wallet</Text>
          <Text style={styles.subtitle}>
            Your recovery phrase will be shown on the next screen. Keep it safe!
          </Text>
          {/* Integration with night-chain-security for wallet creation */}
        </View>
      )}

      {step === 'restore' && (
        <View>
          <Text style={styles.title}>Restore Wallet</Text>
          <Text style={styles.subtitle}>
            Enter your 12 or 24 word recovery phrase
          </Text>
          {/* Integration with night-chain-security for wallet restoration */}
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f7fa',
  },
  content: {
    padding: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#2d3748',
    marginBottom: 8,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: '#718096',
    marginBottom: 32,
    textAlign: 'center',
    lineHeight: 24,
  },
  option: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  optionEmoji: {
    fontSize: 48,
    textAlign: 'center',
    marginBottom: 12,
  },
  optionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#2d3748',
    marginBottom: 8,
    textAlign: 'center',
  },
  optionDesc: {
    fontSize: 14,
    color: '#718096',
    textAlign: 'center',
    lineHeight: 20,
  },
});
