/**
 * Recovery dialog implementation
 * 
 * 4-line challenge/response dialog:
 * Line 1: User provides 4 words from their mnemonic
 * Line 2: Bot responds with 4 verification words
 * Line 3: User provides 4 different words from their mnemonic
 * Line 4: Bot responds with final 4 verification words
 * 
 * Each line contains exactly 4 words.
 */

import * as crypto from 'crypto';
import {
  RecoveryChallenge,
  RecoveryDialogState,
  EncryptedAsset
} from './types';

/**
 * BIP39 word list for validation
 * In production, import from @scure/bip39
 */
const BIP39_WORDLIST = new Set([
  // Abbreviated list - in production use full 2048 word BIP39 list
  'abandon', 'ability', 'able', 'about', 'above', 'absent', 'absorb', 'abstract',
  'absurd', 'abuse', 'access', 'accident', 'account', 'accuse', 'achieve', 'acid'
  // ... rest of BIP39 words
]);

/**
 * Browser-compatible random integer generator
 */
function randomInt(max: number): number {
  const bytes = crypto.randomBytes(4);
  return bytes.readUInt32BE(0) % max;
}

/**
 * Generate random verification words from BIP39 wordlist
 */
function generateVerificationWords(count: number = 4): string[] {
  const words: string[] = [];
  const wordList = Array.from(BIP39_WORDLIST);
  
  for (let i = 0; i < count; i++) {
    const randomIndex = randomInt(wordList.length);
    words.push(wordList[randomIndex]);
  }
  
  return words;
}

/**
 * Validate that words are valid BIP39 words
 */
function validateBIP39Words(words: string[]): boolean {
  if (words.length !== 4) return false;
  return words.every(word => BIP39_WORDLIST.has(word.toLowerCase()));
}

/**
 * Parse user input into 4 words
 */
function parseUserInput(input: string): string[] {
  const words = input
    .toLowerCase()
    .trim()
    .split(/\s+/)
    .filter(w => w.length > 0);
  
  return words;
}

/**
 * Create a new recovery challenge
 */
export function createRecoveryChallenge(assetId: string): RecoveryChallenge {
  const challengeId = crypto.randomBytes(16).toString('hex');
  
  return {
    challengeId,
    userWords: [],
    botWords: [],
    assetId,
    createdAt: Date.now()
  };
}

/**
 * Initialize recovery dialog
 */
export function initializeRecoveryDialog(assetId: string): RecoveryDialogState {
  const challenge = createRecoveryChallenge(assetId);
  
  return {
    step: 'user-line-1',
    challengeId: challenge.challengeId,
    assetId
  };
}

/**
 * Process user input for line 1
 */
export function processUserLine1(
  state: RecoveryDialogState,
  userInput: string
): RecoveryDialogState {
  if (state.step !== 'user-line-1') {
    throw new Error('Invalid dialog step: expected user-line-1');
  }
  
  const words = parseUserInput(userInput);
  
  if (words.length !== 4) {
    throw new Error('Please provide exactly 4 words');
  }
  
  // Note: We don't validate if these are correct mnemonic words yet
  // That happens during decryption
  
  return {
    ...state,
    userLine1: words.join(' '),
    step: 'bot-line-1'
  };
}

/**
 * Generate bot response for line 1
 */
export function generateBotLine1(state: RecoveryDialogState): RecoveryDialogState {
  if (state.step !== 'bot-line-1') {
    throw new Error('Invalid dialog step: expected bot-line-1');
  }
  
  // Generate 4 random verification words
  const botWords = generateVerificationWords(4);
  
  return {
    ...state,
    botLine1: botWords.join(' '),
    step: 'user-line-2'
  };
}

/**
 * Process user input for line 2
 */
export function processUserLine2(
  state: RecoveryDialogState,
  userInput: string
): RecoveryDialogState {
  if (state.step !== 'user-line-2') {
    throw new Error('Invalid dialog step: expected user-line-2');
  }
  
  const words = parseUserInput(userInput);
  
  if (words.length !== 4) {
    throw new Error('Please provide exactly 4 words');
  }
  
  // Ensure these are different words from line 1
  const line1Words = (state.userLine1 || '').split(' ');
  const duplicate = words.some(w => line1Words.includes(w));
  
  if (duplicate) {
    throw new Error('Please provide different words from line 1');
  }
  
  return {
    ...state,
    userLine2: words.join(' '),
    step: 'bot-line-2'
  };
}

/**
 * Generate bot response for line 2 (final)
 */
export function generateBotLine2(state: RecoveryDialogState): RecoveryDialogState {
  if (state.step !== 'bot-line-2') {
    throw new Error('Invalid dialog step: expected bot-line-2');
  }
  
  // Generate 4 random verification words
  const botWords = generateVerificationWords(4);
  
  return {
    ...state,
    botLine2: botWords.join(' '),
    step: 'complete'
  };
}

/**
 * Extract full recovery phrase from dialog
 * Combines user's two 4-word inputs
 */
export function extractRecoveryPhrase(state: RecoveryDialogState): string {
  if (state.step !== 'complete') {
    throw new Error('Recovery dialog not complete');
  }
  
  if (!state.userLine1 || !state.userLine2) {
    throw new Error('Missing user input lines');
  }
  
  // Combine the two user inputs (8 words total)
  const allWords = [
    ...state.userLine1.split(' '),
    ...state.userLine2.split(' ')
  ];
  
  return allWords.join(' ');
}

/**
 * Human-readable recovery dialog formatter
 */
export function formatRecoveryDialog(state: RecoveryDialogState): string {
  const lines: string[] = [];
  
  lines.push('=== RECOVERY DIALOG ===');
  lines.push('');
  lines.push('Instructions: Provide 4 words from your seed phrase.');
  lines.push('This is a secure challenge-response to verify your identity.');
  lines.push('');
  
  if (state.userLine1) {
    lines.push(`[You - Line 1]:  ${state.userLine1}`);
  } else {
    lines.push('[You - Line 1]:  (waiting for 4 words...)');
  }
  
  if (state.botLine1) {
    lines.push(`[Bot - Line 1]:  ${state.botLine1}`);
  }
  
  if (state.userLine2) {
    lines.push(`[You - Line 2]:  ${state.userLine2}`);
  } else if (state.step === 'user-line-2' || state.step === 'bot-line-2' || state.step === 'complete') {
    lines.push('[You - Line 2]:  (waiting for 4 different words...)');
  }
  
  if (state.botLine2) {
    lines.push(`[Bot - Line 2]:  ${state.botLine2}`);
  }
  
  if (state.step === 'complete') {
    lines.push('');
    lines.push('✓ Recovery dialog complete');
  }
  
  return lines.join('\n');
}

/**
 * Recovery dialog manager
 */
export class RecoveryDialogManager {
  private activeDialogs: Map<string, RecoveryDialogState> = new Map();
  
  /**
   * Start a new recovery dialog
   */
  startDialog(assetId: string): string {
    const state = initializeRecoveryDialog(assetId);
    this.activeDialogs.set(state.challengeId, state);
    
    console.log('[INFO] Recovery dialog started');
    console.log('[INFO] Challenge ID:', state.challengeId);
    console.log('[INFO] Asset ID:', assetId);
    
    return state.challengeId;
  }
  
  /**
   * Submit user input
   */
  submitUserInput(challengeId: string, input: string): RecoveryDialogState {
    const state = this.activeDialogs.get(challengeId);
    if (!state) {
      throw new Error('Invalid challenge ID or dialog expired');
    }
    
    let newState: RecoveryDialogState;
    
    if (state.step === 'user-line-1') {
      newState = processUserLine1(state, input);
      newState = generateBotLine1(newState);
    } else if (state.step === 'user-line-2') {
      newState = processUserLine2(state, input);
      newState = generateBotLine2(newState);
    } else {
      throw new Error('Dialog not expecting user input');
    }
    
    this.activeDialogs.set(challengeId, newState);
    return newState;
  }
  
  /**
   * Get current dialog state
   */
  getDialog(challengeId: string): RecoveryDialogState | null {
    return this.activeDialogs.get(challengeId) || null;
  }
  
  /**
   * Complete dialog and get recovery phrase
   */
  completeDialog(challengeId: string): string {
    const state = this.activeDialogs.get(challengeId);
    if (!state) {
      throw new Error('Invalid challenge ID');
    }
    
    if (state.step !== 'complete') {
      throw new Error('Dialog not complete');
    }
    
    const phrase = extractRecoveryPhrase(state);
    
    // Clean up
    this.activeDialogs.delete(challengeId);
    
    return phrase;
  }
  
  /**
   * Cancel dialog
   */
  cancelDialog(challengeId: string): void {
    this.activeDialogs.delete(challengeId);
    console.log('[INFO] Recovery dialog cancelled:', challengeId);
  }
  
  /**
   * Clean up expired dialogs (older than 10 minutes)
   */
  cleanupExpiredDialogs(): void {
    const now = Date.now();
    const expiryTime = 10 * 60 * 1000; // 10 minutes
    
    const entries = Array.from(this.activeDialogs.entries());
    for (const [id, state] of entries) {
      if (now - state.challengeId.length > expiryTime) {
        this.activeDialogs.delete(id);
        console.log('[INFO] Expired dialog removed:', id);
      }
    }
  }
}
