# Cardano Stats Bot

## Description
Posts hourly Cardano blockchain statistics to Discord including ADA price, USDCx total minted, and top 10 CNT tokens by liquidity, volume, and market cap.

## When to Use
- Automatically triggered via cron job every hour
- Can be manually triggered for testing

## Data Sources
1. **CoinGecko API** - ADA price and 24h change (free, no key)
2. **Blockfrost API** - USDCx total supply (requires API key)
3. **Minswap API** - Top 10 CNT tokens (free, no key)

## Configuration
- USDCx Policy ID: `1f3aec8bfe7ea4fe14c5f121e2a92e301afe414147860d557cac7e34`
- Discord Channel: `#cardano-stats` (1478116857595695407)
- Blockfrost API Key: Stored in environment

## Process

### Step 1: Fetch ADA Price
```bash
curl "https://api.coingecko.com/api/v3/simple/price?ids=cardano&vs_currencies=usd&include_24hr_change=true"
```

### Step 2: Fetch USDCx Total Supply
```bash
curl "https://cardano-mainnet.blockfrost.io/api/v0/assets/1f3aec8bfe7ea4fe14c5f121e2a92e301afe414147860d557cac7e34" \
  -H "project_id: YOUR_KEY"
```

### Step 3: Fetch Top 10 CNTs (3 categories)
```bash
# By Liquidity
curl -X POST "https://api-mainnet-prod.minswap.org/v1/assets/metrics" \
  -H "Content-Type: application/json" \
  -d '{"limit":10,"only_verified":true,"sort_field":"liquidity","sort_direction":"desc","currency":"usd"}'

# By 24h Volume
curl -X POST "https://api-mainnet-prod.minswap.org/v1/assets/metrics" \
  -H "Content-Type: application/json" \
  -d '{"limit":10,"only_verified":true,"sort_field":"volume_24h","sort_direction":"desc","currency":"usd"}'

# By Market Cap
curl -X POST "https://api-mainnet-prod.minswap.org/v1/assets/metrics" \
  -H "Content-Type: application/json" \
  -d '{"limit":10,"only_verified":true,"sort_field":"market_cap","sort_direction":"desc","currency":"usd"}'
```

### Step 4: Format and Post to Discord

Format example:
```
🟢 ADA: $0.85 (+3.2% 24h)
💵 USDCx Minted: $125,432,890

📈 Top 10 CNTs by Liquidity:
1. MIN - $45.2M (+12%)
2. WMT - $32.1M (-5%)
3. SHEN - $28.5M (+2%)
...

📊 Top 10 CNTs by 24h Volume:
1. SHEN - $8.5M (+15%)
2. MILK - $6.2M (-3%)
...

💰 Top 10 CNTs by Market Cap:
1. MIN - $120M (+8%)
2. WMT - $95M (-2%)
...
```

Post to Discord using message tool with channel ID.

## Implementation Notes
- Use exec tool to call APIs via PowerShell Invoke-RestMethod
- Parse JSON responses
- Format numbers with appropriate abbreviations (M for millions)
- Use emoji to indicate price movement (🟢 up, 🔴 down)
- Handle API failures gracefully with error messages
