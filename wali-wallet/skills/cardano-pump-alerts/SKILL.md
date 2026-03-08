# Cardano Pump Alert Bot

## Description
Monitors Cardano CNT tokens for rapid price increases and posts real-time alerts to Discord. Detects pumps of +10% in 10 minutes and provides follow-up updates 5 minutes later.

## When to Use
- Automatically triggered via cron job every 2 minutes
- Tracks price movements for quick trade opportunities

## Data Sources
- **Minswap API** - Real-time token price data (free, no key required)

## Configuration
- Discord Channel: `#pump-alerts` (1478117022448488579)
- Alert Threshold: +10% in 10 minutes
- Follow-up: 5 minutes after initial alert
- Monitoring Interval: Every 2 minutes

## Alert Logic

### Initial Alert (+10% in 10 minutes)
```
🔥 PUMP ALERT! 🔥
Token: MILK
Price: $0.042 → $0.089 (+112% in 10min)
Volume 24h: $1.2M
Liquidity: $450K
Exchange: Minswap
```

### Follow-up Alert (5 minutes later)
```
📊 UPDATE: MILK
Price now: $0.095 (+7% since alert)
Status: 🟢 Still pumping!
```

OR

```
📊 UPDATE: MILK
Price now: $0.082 (-8% since alert)
Status: 🔴 Cooling off
```

## State Management
- Store price snapshots in JSON file
- Track alerted tokens to avoid spam
- Schedule follow-ups automatically

## Process

### Every 2 Minutes:
1. Fetch top 50 tokens by volume from Minswap
2. Compare current price to price from 10 minutes ago
3. If +10% or more → Post initial alert
4. Schedule follow-up check for 5 minutes later

### Follow-up Logic:
1. Check price 5 minutes after alert
2. Calculate change since alert
3. Post update with status
4. Remove from tracking

## Implementation Notes
- Use state file: `pump-state.json`
- Clean up old state entries (>1 hour)
- Handle API failures gracefully
- Avoid duplicate alerts for same token
