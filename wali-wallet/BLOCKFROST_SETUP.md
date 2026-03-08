# Blockfrost Setup Guide for wAli Wallet

Complete guide to integrating Blockfrost API with wAli for production Cardano mainnet operations.

## 🎯 Overview

Blockfrost is a production-grade Cardano blockchain API service that provides:
- Real-time blockchain data
- Transaction submission
- UTXO queries
- Native token information
- ADA Handle resolution
- High availability and reliability

## 🔑 Getting Your API Key

### 1. Sign Up for Blockfrost

1. Visit [https://blockfrost.io](https://blockfrost.io)
2. Click "Sign Up" or "Get Started"
3. Create an account with your email
4. Verify your email address

### 2. Create a Project

1. Log into your Blockfrost dashboard
2. Click "Add Project"
3. Choose network:
   - **Mainnet** - For production use with real ADA
   - **Testnet** - For development and testing
4. Name your project (e.g., "wAli Wallet Mainnet")
5. Click "Create Project"

### 3. Get Your API Key

1. In your project dashboard, find your **Project ID**
2. Copy the full project ID (format: `mainnet[random_string]` or `testnet[random_string]`)
3. **Keep this secret!** Treat it like a password

Example project IDs:
- Mainnet: `mainnetehvvvJVoJUAz5DFJJz2L9fHZmkXlXTMP`
- Testnet: `testnetXYZ123ABCdefGHI456...`

## ⚙️ Configuration

### Option 1: Environment Variables (Recommended)

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API key:
   ```env
   BLOCKFROST_PROJECT_ID=mainnetehvvvJVoJUAz5DFJJz2L9fHZmkXlXTMP
   CARDANO_NETWORK=mainnet
   NODE_ENV=production
   ```

3. Make sure `.env` is in `.gitignore` (already configured)

### Option 2: Programmatic Configuration

```typescript
import { WaliEngine } from './src/wali-engine';

const wali = new WaliEngine({
  network: 'mainnet',
  blockfrost: {
    projectId: 'mainnetehvvvJVoJUAz5DFJJz2L9fHZmkXlXTMP',
    network: 'mainnet',
  },
});

await wali.initialize();
```

### Option 3: Web Extension Configuration

For browser extensions, configure in `wallet-ui-interface/web-extension/src/config.ts`:

```typescript
import { getConfig } from './config';

const config = getConfig();
// Blockfrost will be initialized automatically
```

## 🧪 Testing Your Integration

### 1. Run Integration Tests

```bash
# Make sure .env is configured first
npm run test -- blockfrost-integration.test.ts
```

### 2. Test Manually

```typescript
import { BlockfrostAPI } from './src/cardano/blockfrost-api';

const blockfrost = new BlockfrostAPI({
  projectId: process.env.BLOCKFROST_PROJECT_ID!,
  network: 'mainnet',
});

// Test health
const health = await blockfrost.healthCheck();
console.log('Blockfrost healthy:', health.healthy);

// Test balance query
const balance = await blockfrost.getBalance('addr1...');
console.log('Balance:', balance);
```

## 📊 Rate Limits

Blockfrost has different rate limits based on your plan:

### Free Tier
- **50,000 requests/day**
- **10 requests/second**
- Perfect for development and testing

### Paid Tiers
- Higher rate limits
- Priority support
- Better performance

### Handling Rate Limits

wAli automatically handles rate limiting with:
- **Retry logic** - Exponential backoff on 429 errors
- **Caching** - Reduces redundant API calls
- **Request queuing** - Prevents burst requests

Configure retry behavior:
```typescript
const blockfrost = new BlockfrostAPI({
  projectId: 'your_project_id',
  network: 'mainnet',
  maxRetries: 3,        // Number of retry attempts
  retryDelayMs: 1000,   // Initial delay (increases exponentially)
  cacheEnabled: true,   // Enable response caching
  cacheTTL: 30000,      // Cache time-to-live (30 seconds)
});
```

## 🔒 Security Best Practices

### ✅ DO:
- Store API keys in `.env` files
- Add `.env` to `.gitignore`
- Use environment variables in production
- Rotate API keys periodically
- Monitor API usage in Blockfrost dashboard
- Use testnet for development

### ❌ DON'T:
- Commit API keys to version control
- Share API keys publicly
- Hardcode API keys in source code
- Expose API keys in client-side code
- Use mainnet keys for testing

### API Key Rotation

If your key is compromised:

1. Go to Blockfrost dashboard
2. Revoke the old key
3. Generate a new key
4. Update `.env` with new key
5. Restart your application

## 🚀 Production Deployment

### Pre-Deployment Checklist

- [ ] Test on testnet first
- [ ] Verify API key is set in production environment
- [ ] Confirm `.env` is not committed
- [ ] Test all critical operations (balance, UTXOs, transactions)
- [ ] Set up monitoring and alerts
- [ ] Document API key location for team
- [ ] Configure error handling and logging
- [ ] Test rate limit handling
- [ ] Verify caching is enabled
- [ ] Check mainnet/testnet network configuration

### Environment Setup

For different environments:

**Development** (`.env.development`):
```env
BLOCKFROST_PROJECT_ID=testnetABC123...
CARDANO_NETWORK=testnet
NODE_ENV=development
```

**Production** (`.env.production`):
```env
BLOCKFROST_PROJECT_ID=mainnetXYZ789...
CARDANO_NETWORK=mainnet
NODE_ENV=production
```

### Vercel/Netlify Deployment

Add environment variables in your hosting platform:
1. Go to project settings
2. Add environment variables:
   - `BLOCKFROST_PROJECT_ID` = your mainnet key
   - `CARDANO_NETWORK` = `mainnet`
3. Redeploy

## 📈 Monitoring

### Check API Usage

1. Log into Blockfrost dashboard
2. View usage statistics
3. Monitor:
   - Request count
   - Error rates
   - Rate limit hits
   - Response times

### Application Logging

Enable Blockfrost request logging:

```typescript
// Custom logging middleware
blockfrost.client.interceptors.request.use(config => {
  console.log(`Blockfrost request: ${config.method} ${config.url}`);
  return config;
});
```

## 🐛 Troubleshooting

### Common Issues

#### 1. "Invalid API Key" Error
- **Cause**: Wrong or expired project ID
- **Solution**: Verify key in Blockfrost dashboard, regenerate if needed

#### 2. "Rate Limit Exceeded"
- **Cause**: Too many requests
- **Solution**: Enable caching, implement request queuing, upgrade plan

#### 3. "Network Mismatch"
- **Cause**: Using testnet key with mainnet network
- **Solution**: Ensure `BLOCKFROST_PROJECT_ID` matches `CARDANO_NETWORK`

#### 4. "Resource Not Found"
- **Cause**: Invalid address or non-existent transaction
- **Solution**: Verify input data, check network (mainnet vs testnet)

#### 5. Connection Timeouts
- **Cause**: Network issues or Blockfrost downtime
- **Solution**: Check Blockfrost status page, verify internet connection

### Debug Mode

Enable verbose logging:

```typescript
const blockfrost = new BlockfrostAPI({
  projectId: process.env.BLOCKFROST_PROJECT_ID!,
  network: 'mainnet',
});

// Log all requests
blockfrost.client.interceptors.request.use(
  config => {
    console.log('📤 Request:', config.url);
    return config;
  }
);

// Log all responses
blockfrost.client.interceptors.response.use(
  response => {
    console.log('📥 Response:', response.status);
    return response;
  }
);
```

## 📚 API Reference

### Main Methods

All methods are available through `CardanoWallet` or `BlockfrostAPI`:

#### Balance Queries
```typescript
const balance = await wallet.getBalance(address);
// Returns: { chain, address, native: { amount, symbol, decimals }, tokens }
```

#### UTXO Retrieval
```typescript
const utxos = await wallet.getUTXOs(address);
// Returns: Array<{ txHash, index, amount, assets }>
```

#### Transaction History
```typescript
const txs = await wallet.getTransactionHistory(address, limit);
// Returns: Array<Transaction>
```

#### ADA Handle Resolution
```typescript
const address = await wallet.resolveAdaHandle('$handle');
// Returns: string | null
```

#### Transaction Submission
```typescript
const txHash = await wallet.submitTransaction(signedTxHex);
// Returns: transaction hash
```

#### Fee Estimation
```typescript
const fees = await wallet.estimateFees();
// Returns: { slow, medium, fast }
```

#### Asset Metadata
```typescript
const metadata = await wallet.getAssetMetadata(assetId);
// Returns: asset details with on-chain metadata
```

## 🔗 Resources

- [Blockfrost Documentation](https://docs.blockfrost.io/)
- [Blockfrost Status Page](https://status.blockfrost.io/)
- [Cardano Developer Portal](https://developers.cardano.org/)
- [wAli Developer Guide](./WALI_DEVELOPER_GUIDE.md)
- [wAli User Guide](./WALI_USER_GUIDE.md)

## 💡 Tips

1. **Use testnet first** - Always develop on testnet before mainnet
2. **Enable caching** - Reduce API calls and costs
3. **Monitor usage** - Keep track of your request quota
4. **Handle errors gracefully** - Network issues happen, plan for them
5. **Use retry logic** - Built into wAli, but tune for your needs
6. **Keep keys secure** - Never commit or expose API keys

## 🆘 Support

- **Blockfrost Support**: support@blockfrost.io
- **wAli Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Cardano Community**: [Cardano Forum](https://forum.cardano.org/)

---

**Ready to deploy? 🦭⛓️**

Your wAli wallet is now connected to the real Cardano blockchain via Blockfrost!
