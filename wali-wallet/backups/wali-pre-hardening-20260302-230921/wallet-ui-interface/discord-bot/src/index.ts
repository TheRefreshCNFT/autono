/**
 * Discord bot for conversational wallet interface
 * Allows users to interact with their wallet through Discord DMs
 */

import { Client, GatewayIntentBits, Message, EmbedBuilder } from 'discord.js';
import { CommandParser, TransactionPreview } from '@wallet-ui/shared';
import * as dotenv from 'dotenv';

dotenv.config();

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.DirectMessages,
    GatewayIntentBits.MessageContent,
  ],
});

const parser = new CommandParser();

// Store user sessions (in production, use proper database)
const userSessions = new Map<string, any>();

client.on('ready', () => {
  console.log(`✅ Wallet bot logged in as ${client.user?.tag}`);
});

client.on('messageCreate', async (message: Message) => {
  // Ignore bot messages
  if (message.author.bot) return;

  // Only respond to DMs for security
  if (!message.guild && message.channel.type === 1) {
    await handleDirectMessage(message);
  }
});

async function handleDirectMessage(message: Message) {
  const userId = message.author.id;
  const input = message.content.trim();

  try {
    // Parse the command
    const parsed = parser.parse(input);

    // Check for ambiguities
    if (parsed.ambiguities.length > 0) {
      const ambiguityMessage = parsed.ambiguities
        .map(a => `• ${a.message}`)
        .join('\n');

      await message.reply(ambiguityMessage);
      return;
    }

    // Process command based on type
    if (parsed.intent.type === 'send') {
      await handleSendCommand(message, parsed);
    } else {
      await message.reply('Command understood! (Integration with wallet-core-engine needed)');
    }
  } catch (error: any) {
    await message.reply(`❌ Error: ${error.message || 'Something went wrong'}`);
  }
}

async function handleSendCommand(message: Message, parsed: any) {
  // Mock transaction preview
  const preview: TransactionPreview = {
    intent: parsed.intent,
    fee: '0.17',
    feeAsset: {
      chain: 'cardano',
      type: 'native',
      symbol: 'ADA',
      decimals: 6,
      balance: '0',
    },
    totalCost: parsed.intent.amount
      ? (parseFloat(parsed.intent.amount) + 0.17).toFixed(6)
      : '0.17',
    humanReadable: `Send ${parsed.intent.amount} ${parsed.intent.asset?.symbol} to ${parsed.intent.to?.address}`,
    warnings: [],
  };

  // Create embed for transaction preview
  const embed = new EmbedBuilder()
    .setColor('#667eea')
    .setTitle('🔍 Transaction Preview')
    .setDescription(preview.humanReadable)
    .addFields(
      { name: 'Network Fee', value: `${preview.fee} ${preview.feeAsset.symbol}`, inline: true },
      { name: 'Total Cost', value: `${preview.totalCost} ${parsed.intent.asset?.symbol}`, inline: true }
    )
    .setFooter({ text: 'React with ✅ to confirm, ❌ to cancel' })
    .setTimestamp();

  const previewMessage = await message.reply({ embeds: [embed] });

  // Add reaction buttons
  await previewMessage.react('✅');
  await previewMessage.react('❌');

  // Wait for user reaction
  const filter = (reaction: any, user: any) => {
    return ['✅', '❌'].includes(reaction.emoji.name) && user.id === message.author.id;
  };

  try {
    const collected = await previewMessage.awaitReactions({
      filter,
      max: 1,
      time: 60000, // 1 minute timeout
      errors: ['time'],
    });

    const reaction = collected.first();

    if (reaction?.emoji.name === '✅') {
      await message.reply('✅ Transaction submitted! (Integration with wallet-core-engine needed)');
    } else {
      await message.reply('❌ Transaction cancelled.');
    }
  } catch (error) {
    await message.reply('⏰ Transaction timed out. Please try again.');
  }
}

// Error handling
client.on('error', (error) => {
  console.error('Discord client error:', error);
});

// Login
const token = process.env.DISCORD_BOT_TOKEN;
if (!token) {
  console.error('❌ DISCORD_BOT_TOKEN not found in environment variables');
  process.exit(1);
}

client.login(token);
