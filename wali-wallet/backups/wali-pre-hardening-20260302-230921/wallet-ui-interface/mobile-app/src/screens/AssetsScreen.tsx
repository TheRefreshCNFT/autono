import React from 'react';
import { View, Text, FlatList, StyleSheet, Image } from 'react-native';
import { useWalletStore } from '../store/wallet';
import { formatAssetAmount, sortAssets, getAssetColor } from '@wallet-ui/shared';

export const AssetsScreen: React.FC = () => {
  const { walletState } = useWalletStore();
  const sortedAssets = sortAssets(walletState.assets);

  return (
    <View style={styles.container}>
      <FlatList
        data={sortedAssets}
        keyExtractor={(item, idx) => `${item.symbol}-${idx}`}
        renderItem={({ item }) => (
          <View style={styles.assetItem} accessible={true} accessibilityRole="summary">
            <View
              style={[styles.assetIcon, { backgroundColor: getAssetColor(item.symbol) }]}
            >
              {item.metadata?.image ? (
                <Image source={{ uri: item.metadata.image }} style={styles.assetImage} />
              ) : (
                <Text style={styles.assetIconText}>{item.symbol[0]}</Text>
              )}
            </View>
            <View style={styles.assetInfo}>
              <Text style={styles.assetSymbol}>{item.symbol}</Text>
              {item.metadata?.name && (
                <Text style={styles.assetName}>{item.metadata.name}</Text>
              )}
            </View>
            <Text style={styles.assetBalance}>
              {formatAssetAmount(item.balance, item.decimals)}
            </Text>
          </View>
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No assets found</Text>
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
  assetItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    padding: 16,
    marginHorizontal: 12,
    marginTop: 12,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 1,
  },
  assetIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  assetImage: {
    width: 48,
    height: 48,
    borderRadius: 24,
  },
  assetIconText: {
    color: 'white',
    fontSize: 20,
    fontWeight: '600',
  },
  assetInfo: {
    flex: 1,
  },
  assetSymbol: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2d3748',
  },
  assetName: {
    fontSize: 13,
    color: '#718096',
    marginTop: 2,
  },
  assetBalance: {
    fontSize: 16,
    fontWeight: '500',
    color: '#2d3748',
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
