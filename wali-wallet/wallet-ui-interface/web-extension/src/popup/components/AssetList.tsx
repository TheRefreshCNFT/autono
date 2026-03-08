import React from 'react';
import { Asset, formatAssetAmount, sortAssets, getAssetColor } from '@wallet-ui/shared';
import './AssetList.css';

interface AssetListProps {
  assets: Asset[];
  compact?: boolean;
}

export const AssetList: React.FC<AssetListProps> = ({ assets, compact = false }) => {
  const sortedAssets = sortAssets(assets);

  if (assets.length === 0) {
    return (
      <div className="asset-list-empty" role="status">
        <p>No assets found</p>
      </div>
    );
  }

  return (
    <div className={`asset-list ${compact ? 'compact' : ''}`} role="list" aria-label="Asset list">
      {sortedAssets.map((asset: Asset, idx: number) => (
        <div
          key={`${asset.symbol}-${idx}`}
          className="asset-item"
          role="listitem"
          aria-label={`${asset.symbol}: ${formatAssetAmount(asset.balance, asset.decimals)}`}
        >
          <div className="asset-icon" style={{ backgroundColor: getAssetColor(asset.symbol) }}>
            {asset.metadata?.image ? (
              <img src={asset.metadata.image} alt={asset.symbol} />
            ) : (
              <span aria-hidden="true">{asset.symbol[0]}</span>
            )}
          </div>
          <div className="asset-info">
            <div className="asset-symbol">{asset.symbol}</div>
            {!compact && asset.metadata?.name && (
              <div className="asset-name">{asset.metadata.name}</div>
            )}
          </div>
          <div className="asset-balance">
            {formatAssetAmount(asset.balance, asset.decimals)}
          </div>
        </div>
      ))}
    </div>
  );
};
