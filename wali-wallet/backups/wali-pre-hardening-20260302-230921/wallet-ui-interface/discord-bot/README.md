# Discord Bot - Conversational Wallet

Discord bot interface for the conversational wallet, allowing users to manage their wallet through Discord DMs.

## Features

- Natural language command processing in Discord DMs
- Transaction previews with reaction-based confirmation
- Secure DM-only operation (no public channel exposure)
- Integration with wallet-core-engine for blockchain operations

## Setup

1. **Create a Discord Bot**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Add a bot user
   - Copy the bot token

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your DISCORD_BOT_TOKEN
   ```

3. **Install Dependencies**
   ```bash
   npm install
   ```

4. **Build and Run**
   ```bash
   npm run build
   npm start
   ```

   Or for development:
   ```bash
   npm run dev
   ```

## Usage

1. Invite the bot to your Discord server or DM it directly
2. Send wallet commands via DM:
   - `send 10 ADA to addr1...`
   - `show balance`
   - `show transactions`
3. Confirm transactions using emoji reactions (✅/❌)

## Security Notes

- Bot only responds to DMs for privacy
- Never share wallet keys or recovery phrases through Discord
- Use this for convenience, not high-value transactions
- Consider implementing additional authentication

## Integration Points

- **wallet-core-engine**: Transaction building and submission
- **night-chain-security**: Key management and signing
- **@wallet-ui/shared**: Command parsing and transaction preview

## Commands

Same natural language commands as web extension and mobile app:
- `send <amount> <currency> to <address>`
- `show balance`
- `show transactions`
- `receive`
- etc.
