# Conversational Wallet Interface

A multi-platform conversational wallet interface for Cardano and Bitcoin, supporting natural language commands for wallet operations.

## Project Structure

```
wallet-ui-interface/
├── web-extension/       # Chrome/Firefox browser extension
├── mobile-app/          # React Native cross-platform app
├── shared/              # Shared components and logic
├── discord-bot/         # Optional Discord bot interface
└── README.md
```

## Features

- **Natural Language Commands**: "send 10 ADA to addr1..." or "send 50 to $handle"
- **Conversational UX**: Smart replies for ambiguous inputs
- **Transaction Previews**: Human-readable explanations before signing
- **dApp Integration**: Permission system for dApp connections
- **Multi-Asset Support**: ADA, BTC, tokens, and NFTs
- **Accessibility**: WCAG 2.1 AA compliant

## Integration Points

- **wallet-core-engine**: Blockchain operations and transaction building
- **night-chain-security**: Key management and recovery dialogs

## Getting Started

See individual platform directories for setup instructions:
- [Web Extension](./web-extension/README.md)
- [Mobile App](./mobile-app/README.md)
- [Discord Bot](./discord-bot/README.md) (optional)

## Development

Each platform shares common logic through the `shared/` directory:
- Command parser
- Transaction builder
- UI components
- State management
