# wAli dApp Integration Guide

**Connect your dApp to wAli's wallet infrastructure 🔌**

## Quick Start

### 1. Register Your dApp

```bash
curl -X POST https://api.wali.app/v1/dapps/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Awesome dApp",
    "description": "DeFi platform for...",
    "website": "https://myawesomeapp.io",
    "contactEmail": "dev@myawesomeapp.io",
    "tier": "basic"
  }'
```

**Response:**
```json
{
  "dappId": "dapp_myawesomeapp_abc123",
  "apiKey": "wali_sk_live_abc123...",
  "status": "trial",
  "trialExpiresAt": "2026-03-16T00:00:00Z"
}
```

### 2. Install SDK

```bash
npm install @wali/sdk
```

### 3. Initialize SDK

```typescript
import { WaliSDK } from '@wali/sdk';

const wali = new WaliSDK({
  apiKey: process.env.WALI_API_KEY,
  network: 'mainnet',
});
```

### 4. Connect User Wallet

```typescript
// Request wallet connection
const wallet = await wali.connectWallet({
  userId: 'user-123',
  permissions: ['read_balance', 'sign_transactions'],
});

console.log('Connected:', wallet.address);
```

### 5. Read Balance

```typescript
const balance = await wali.getBalance(wallet.address);

console.log(`ADA: ${balance.native.amount}`);
console.log(`Tokens: ${balance.tokens?.length || 0}`);
```

### 6. Send Transaction

```typescript
const tx = await wali.sendTransaction({
  from: wallet.address,
  to: 'addr1...',
  amount: '10000000', // 10 ADA in lovelace
  memo: 'Payment for service',
});

console.log('Transaction hash:', tx.hash);
```

## API Reference

### Authentication

All API requests require authentication via API key:

```
Authorization: Bearer wali_sk_live_abc123...
```

### Endpoints

#### **POST /v1/wallet/connect**

Connect a user's wallet to your dApp.

**Request:**
```json
{
  "userId": "string",
  "permissions": ["read_balance", "sign_transactions"]
}
```

**Response:**
```json
{
  "address": "addr1...",
  "sessionId": "sess_abc123",
  "expiresAt": "2026-03-02T20:00:00Z"
}
```

#### **GET /v1/wallet/:address/balance**

Get wallet balance (ADA + native tokens).

**Response:**
```json
{
  "chain": "cardano",
  "address": "addr1...",
  "native": {
    "amount": "5000000",
    "symbol": "ADA",
    "decimals": 6
  },
  "tokens": [
    {
      "policyId": "...",
      "assetName": "...",
      "amount": "100",
      "name": "My Token",
      "symbol": "MTK"
    }
  ]
}
```

#### **POST /v1/transactions/send**

Send a transaction (requires user approval).

**Request:**
```json
{
  "from": "addr1...",
  "to": "addr1...",
  "amount": "10000000",
  "memo": "Optional message"
}
```

**Response:**
```json
{
  "txHash": "abc123...",
  "status": "pending",
  "confirmations": 0
}
```

#### **GET /v1/transactions/:hash**

Get transaction status.

**Response:**
```json
{
  "hash": "abc123...",
  "status": "confirmed",
  "confirmations": 5,
  "timestamp": 1709413200000
}
```

#### **GET /v1/dapps/:dappId/analytics**

Get usage analytics for your dApp.

**Response:**
```json
{
  "connectedUsers": 450,
  "maxUsers": 1000,
  "utilizationPercent": 45,
  "tier": "basic",
  "paymentStatus": "paid",
  "daysUntilExpiration": 25
}
```

## Webhooks

Receive real-time notifications for events.

### Setup Webhook

1. Register webhook URL in dashboard or via API:

```bash
curl -X POST https://api.wali.app/v1/dapps/:dappId/webhooks \
  -H "Authorization: Bearer wali_sk_live_..." \
  -d '{"url": "https://myapp.io/webhooks/wali"}'
```

2. Verify webhook signature:

```typescript
import crypto from 'crypto';

function verifyWebhook(payload: string, signature: string, secret: string): boolean {
  const expected = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expected)
  );
}

// In your webhook handler
app.post('/webhooks/wali', (req, res) => {
  const signature = req.headers['x-wali-signature'];
  const isValid = verifyWebhook(
    JSON.stringify(req.body),
    signature,
    process.env.WALI_WEBHOOK_SECRET
  );
  
  if (!isValid) {
    return res.status(401).send('Invalid signature');
  }
  
  // Process webhook event
  const event = req.body;
  console.log('Event type:', event.type);
  
  res.status(200).send('OK');
});
```

### Webhook Events

#### **transaction.confirmed**

```json
{
  "type": "transaction.confirmed",
  "data": {
    "txHash": "abc123...",
    "from": "addr1...",
    "to": "addr1...",
    "amount": "10000000",
    "confirmations": 3
  }
}
```

#### **user.connected**

```json
{
  "type": "user.connected",
  "data": {
    "userId": "user-123",
    "address": "addr1...",
    "sessionId": "sess_abc123"
  }
}
```

#### **subscription.renewed**

```json
{
  "type": "subscription.renewed",
  "data": {
    "dappId": "dapp_myapp_123",
    "tier": "basic",
    "amount": 99,
    "periodEnd": "2026-04-02T00:00:00Z"
  }
}
```

## Pricing Tiers

### Basic - $99/month

**Limits:**
- 1,000 connected users
- 10,000 API requests/day
- Community support

**Best for:**
- Early-stage dApps
- MVPs and prototypes
- Side projects

**Upgrade when:**
- Approaching 800 users
- Need email support
- Want custom branding

### Premium - $299/month

**Limits:**
- 10,000 connected users
- 100,000 API requests/day
- Email support

**Best for:**
- Growing dApps
- Production applications
- Businesses

**Includes:**
- Custom branding
- Advanced analytics
- Webhook notifications
- Priority API access
- 99.9% uptime SLA

**Upgrade when:**
- Approaching 8,000 users
- Need dedicated support
- Want white-label options

### Enterprise - Custom Pricing

**Features:**
- Unlimited users
- Unlimited API requests
- Dedicated infrastructure
- Dedicated support
- White-label options
- On-premise deployment
- Custom SLAs

**Best for:**
- Large-scale dApps
- Enterprise applications
- Institutional clients

**Contact:** enterprise@wali.app

## Payment Methods

### Option 1: Cardano (Recommended)

**Advantages:**
- ✅ Instant settlement
- ✅ Low fees (~0.17 ADA)
- ✅ Transparent verification
- ✅ No intermediaries

**How to pay:**

1. Get payment address:
```bash
curl https://api.wali.app/v1/dapps/:dappId/payment-intent \
  -H "Authorization: Bearer wali_sk_live_..."
```

2. Send ADA from your wallet to the provided address

3. Payment confirmed automatically (3 confirmations)

4. Service activated

### Option 2: Credit Card (Stripe)

**Advantages:**
- ✅ Familiar payment flow
- ✅ Monthly auto-billing
- ✅ Invoice generation

**How to pay:**

1. Visit your dApp dashboard
2. Click "Upgrade Plan"
3. Enter card details
4. Confirm payment

## Code Examples

### React Integration

```typescript
import { WaliProvider, useWali } from '@wali/react';

function App() {
  return (
    <WaliProvider apiKey={process.env.REACT_APP_WALI_API_KEY}>
      <MyDApp />
    </WaliProvider>
  );
}

function MyDApp() {
  const { connect, balance, sendTransaction } = useWali();
  
  const handleConnect = async () => {
    const wallet = await connect({
      userId: 'user-123',
    });
    console.log('Connected:', wallet.address);
  };
  
  return (
    <button onClick={handleConnect}>
      Connect Wallet
    </button>
  );
}
```

### Node.js Backend

```typescript
import { WaliSDK } from '@wali/sdk';

const wali = new WaliSDK({
  apiKey: process.env.WALI_API_KEY,
});

// Create user session
app.post('/api/wallet/connect', async (req, res) => {
  const { userId } = req.body;
  
  const session = await wali.createSession({
    userId,
    permissions: ['read_balance', 'sign_transactions'],
    expiresIn: 3600, // 1 hour
  });
  
  res.json({ sessionId: session.id });
});

// Process payment
app.post('/api/payments', async (req, res) => {
  const { from, to, amount } = req.body;
  
  const tx = await wali.sendTransaction({
    from,
    to,
    amount,
  });
  
  res.json({ txHash: tx.hash });
});
```

## Rate Limits

| Tier | Requests/Day | Requests/Minute |
|------|--------------|-----------------|
| Basic | 10,000 | 100 |
| Premium | 100,000 | 1,000 |
| Enterprise | Unlimited | Unlimited |

**Rate limit headers:**
```
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 9500
X-RateLimit-Reset: 1709413200
```

**429 response:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Try again in 60 seconds."
}
```

## Best Practices

### Security

- ✅ Never expose API keys client-side
- ✅ Use environment variables for secrets
- ✅ Verify webhook signatures
- ✅ Implement HTTPS only
- ✅ Rotate API keys regularly

### Performance

- ✅ Cache balance/transaction data
- ✅ Use webhooks instead of polling
- ✅ Batch API requests when possible
- ✅ Implement retry logic with exponential backoff

### User Experience

- ✅ Show clear connection prompts
- ✅ Display transaction confirmations
- ✅ Handle errors gracefully
- ✅ Support wallet disconnection
- ✅ Respect user privacy

## Support

- **Documentation**: https://docs.wali.app
- **Discord**: https://discord.gg/wali
- **Email**: support@wali.app
- **Status**: https://status.wali.app

## Changelog

### v1.0.0 (2026-03-02)
- Initial release
- Basic, Premium, Enterprise tiers
- Cardano + Stripe payments
- Webhook support

---

**Ready to integrate?** Start your 14-day free trial today! 🚀
