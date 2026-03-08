import React from 'react';
import { View, Text, FlatList, StyleSheet } from 'react-native';

export const TransactionHistoryScreen: React.FC = () => {
  // TODO: Implement with wallet-core-engine transaction history
  const transactions: any[] = [];

  return (
    <View style={styles.container}>
      <FlatList
        data={transactions}
        keyExtractor={item => item.id}
        renderItem={({ item }) => (
          <View style={styles.txItem}>
            <Text style={styles.txType}>{item.type}</Text>
            <Text style={styles.txAmount}>{item.amount}</Text>
          </View>
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No transactions yet</Text>
          </View>
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f7fa',
  },
  txItem: {
    backgroundColor: 'white',
    padding: 16,
    marginHorizontal: 12,
    marginTop: 12,
    borderRadius: 12,
  },
  txType: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2d3748',
  },
  txAmount: {
    fontSize: 14,
    color: '#718096',
    marginTop: 4,
  },
  empty: {
    padding: 48,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: '#718096',
  },
});
