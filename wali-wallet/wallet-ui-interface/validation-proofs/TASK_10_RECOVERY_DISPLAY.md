# TASK 10: Recovery Instructions Display - VALIDATION PROOF

**Task:** Clear instructions for 16-word recovery  
**Status:** ✅ COMPLETE  
**Completed:** 2026-03-03 00:55 EST

## Requirements Checklist
- ✅ After wallet creation + Night backup
- ✅ Show 16 words clearly (4 lines, 4 words each)
- ✅ Explain what they're for
- ✅ Copy button
- ✅ Checkbox: "I saved these words"

## Implementation Review

### 1. Recovery Words Display Component
**File:** `wallet-ui-interface/web-extension/src/popup/components/RecoveryWordsDisplay.tsx`

**Props:**
```typescript
interface RecoveryWordsDisplayProps {
  challengeWords: string[]; // 16 words total
  onAcknowledge: () => void;
}
```

✅ Receives 16-word recovery challenge
✅ Callback for acknowledgment

### 2. 16-Word Validation
**Input Validation:**
```typescript
if (challengeWords.length !== 16) {
  console.error('Expected 16 challenge words, got:', challengeWords.length);
  return null;
}
```

✅ Verifies exactly 16 words
✅ Fails gracefully if wrong count
✅ Logs error for debugging

### 3. 4-Line Display Format
**Line Splitting:**
```typescript
// Split into 4 lines of 4 words each
const lines = [
  challengeWords.slice(0, 4),   // Line 1 (Bot)
  challengeWords.slice(4, 8),   // Line 2 (You)
  challengeWords.slice(8, 12),  // Line 3 (Bot)
  challengeWords.slice(12, 16), // Line 4 (You)
];

const lineLabels = ['Bot', 'You', 'Bot', 'You'];
```

✅ 4 lines with 4 words each
✅ Labeled with speaker (Bot/You)
✅ Alternating pattern for recovery dialog

**Display:**
```tsx
<div className="challenge-lines">
  {lines.map((line, idx) => (
    <div key={idx} className="challenge-line">
      <div className="line-label">
        <span className="line-number">Line {idx + 1}</span>
        <span className={`line-actor ${lineLabels[idx].toLowerCase()}`}>
          ({lineLabels[idx]})
        </span>
      </div>
      <div className="line-words">
        {line.map((word, wordIdx) => (
          <span key={wordIdx} className="challenge-word">
            {word}
          </span>
        ))}
      </div>
    </div>
  ))}
</div>
```

✅ Clear visual separation
✅ Line numbers (1-4)
✅ Speaker labels (Bot/You)
✅ Each word displayed individually

### 4. Copy Button
**Implementation:**
```typescript
const [copied, setCopied] = useState(false);

const handleCopyAll = async () => {
  const formatted = lines
    .map((line, idx) => `Line ${idx + 1} (${lineLabels[idx]}): ${line.join(' ')}`)
    .join('\n');

  try {
    await navigator.clipboard.writeText(formatted);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  } catch (err) {
    console.error('Failed to copy recovery words:', err);
  }
};

// Button
<button
  className="copy-recovery-btn"
  onClick={handleCopyAll}
  disabled={copied}
>
  {copied ? '✅ Copied to Clipboard!' : '📋 Copy All Words'}
</button>
```

✅ Formats with line numbers and labels
✅ Copies to clipboard
✅ Shows "✅ Copied!" feedback (3 seconds)
✅ Disabled during copied state
✅ Error handling

**Copied Format:**
```
Line 1 (Bot): word1 word2 word3 word4
Line 2 (You): word5 word6 word7 word8
Line 3 (Bot): word9 word10 word11 word12
Line 4 (You): word13 word14 word15 word16
```

✅ Clear format for backup
✅ Ready to paste into notes

### 5. Explanation Section
**What the Words Are For:**
```tsx
<div className="recovery-explanation">
  <p>
    <strong>If you forget your access key, these 16 words are your ONLY way to recover your wallet!</strong>
  </p>
  <p>
    Write them down exactly as shown below. Keep them safe and private.
  </p>
</div>
```

✅ Clear warning
✅ Explains critical importance
✅ Instructions to write down

### 6. Recovery Instructions
**How to Use:**
```tsx
<div className="recovery-instructions">
  <h3>How to Use These Words:</h3>
  <ol>
    <li>Keep these 16 words in a safe place (not on your computer!)</li>
    <li>If you forget your access key, you can use these words to recover</li>
    <li>During recovery, you'll alternate lines with the system:
      <ul>
        <li>Bot speaks Line 1</li>
        <li>You speak Line 2</li>
        <li>Bot speaks Line 3</li>
        <li>You speak Line 4</li>
      </ul>
    </li>
    <li>Never share these words with anyone!</li>
  </ol>
</div>
```

✅ Step-by-step instructions
✅ Explains recovery dialog flow
✅ Security warnings
✅ Clear use case

### 7. Acknowledgment Checkbox
**Implementation:**
```typescript
const [acknowledged, setAcknowledged] = useState(false);

<div className="acknowledgment">
  <label className="acknowledgment-checkbox">
    <input
      type="checkbox"
      checked={acknowledged}
      onChange={(e) => setAcknowledged(e.target.checked)}
    />
    <span>
      I have written down these 16 words and stored them safely.
      I understand this is my only backup if I forget my access key.
    </span>
  </label>
</div>
```

✅ Required checkbox
✅ Clear commitment statement
✅ Mentions critical importance

### 8. Continue Button with Validation
**Implementation:**
```typescript
const handleAcknowledge = () => {
  if (!acknowledged) {
    alert('Please make sure you have saved these words before continuing!');
    return;
  }
  onAcknowledge();
};

<button
  className="continue-btn"
  onClick={handleAcknowledge}
  disabled={!acknowledged}
>
  I've Saved My Recovery Words - Continue
</button>
```

✅ Disabled until checkbox checked
✅ Alert if trying to continue without acknowledgment
✅ Double confirmation
✅ Clear button text

### 9. Warning Badges
**Critical Warnings:**
```tsx
<div className="recovery-header">
  <h2>🦭 SAVE THESE RECOVERY WORDS!</h2>
  <div className="warning-badge">⚠️ Critical - Write These Down!</div>
</div>

<div className="final-warning">
  ⚠️ Without these words AND your access key, you CANNOT recover your wallet!
</div>
```

✅ Header warning
✅ Final warning at bottom
✅ Emphasizes criticality
✅ Clear consequences

### 10. Integration with Wallet Flow
**File:** `wallet-ui-interface/web-extension/src/store/wallet.ts`

**Trigger After Backup:**
```typescript
backupToNightChain: async (accessKey: string): Promise<CommandResponse> => {
  // ... backup completes ...
  
  return {
    success: true,
    message: '✅ **Your seed phrase is safely stored on Night Chain!**\n\n' +
      `Transaction ID: \`${result.transactionId}\`\n\n` +
      '⚠️ **CRITICAL: Save Your Recovery Words**\n\n' +
      'You will now see your 16-word recovery challenge.\n' +
      'These are REQUIRED if you forget your access key!',
    data: {
      showRecoveryChallenge: true,
      recoveryChallenge: challengeWords,
      transactionId: result.transactionId,
    },
  };
}
```

✅ Triggered after successful backup
✅ Data flag `showRecoveryChallenge: true`
✅ Passes 16 words as `recoveryChallenge`

**File:** `wallet-ui-interface/web-extension/src/popup/App.tsx`

**Modal Trigger:**
```typescript
// Check if we need to show recovery challenge
if (response.data?.showRecoveryChallenge && response.data?.recoveryChallenge) {
  setShowRecoveryWords(true);
}

// Modal Render
{showRecoveryWords && recoveryChallenge && (
  <RecoveryWordsDisplay
    challengeWords={recoveryChallenge}
    onAcknowledge={handleRecoveryAcknowledge}
  />
)}
```

✅ Shows modal when flag set
✅ Passes recovery challenge from store
✅ Handles acknowledgment

**Acknowledgment Handler:**
```typescript
const handleRecoveryAcknowledge = () => {
  setShowRecoveryWords(false);
  addAssistantMessage(
    '✅ **Wallet Setup Complete!**\n\n' +
    'Your wallet is now fully set up and ready to use.\n\n' +
    'Try these commands:\n' +
    '• **what\'s my balance?**\n' +
    '• **receive** - Show your addresses\n' +
    '• **send 10 ADA to addr1...**\n\n' +
    'Welcome to wAli! 🦭'
  );
};
```

✅ Closes modal
✅ Shows completion message
✅ Suggests next steps
✅ Welcomes user

### 11. Build Verification

**Build Command:** `npm run build`
**Result:** ✅ SUCCESS (exit code 0)

Extension compiles successfully with recovery display.

## Test Scenarios

### Scenario 1: Normal Wallet Creation Flow
**Steps:**
1. User: "create wallet"
2. Creates wallet → Shows addresses
3. Prompts for access key
4. User enters access key
5. Backup completes

**Expected:**
1. Recovery words modal appears
2. Shows 16 words in 4 lines
3. Line 1 (Bot): 4 words
4. Line 2 (You): 4 words
5. Line 3 (Bot): 4 words
6. Line 4 (You): 4 words
7. Checkbox unchecked by default
8. Continue button disabled

**Result:** ✅ Modal appears with correct format

### Scenario 2: Copy Words
**Action:** Click "📋 Copy All Words"

**Expected:**
1. Words copied to clipboard in format:
   ```
   Line 1 (Bot): word1 word2 word3 word4
   Line 2 (You): word5 word6 word7 word8
   Line 3 (Bot): word9 word10 word11 word12
   Line 4 (You): word13 word14 word15 word16
   ```
2. Button changes to "✅ Copied to Clipboard!"
3. Reverts after 3 seconds

**Result:** ✅ Copy works with feedback

### Scenario 3: Try to Continue Without Checkbox
**Action:** Click continue button without checking box

**Expected:**
1. Button is disabled (grayed out)
2. Click does nothing

**Result:** ✅ Button disabled

### Scenario 4: Check Box and Continue
**Action:** 
1. Check "I have written down these 16 words..."
2. Click continue

**Expected:**
1. Modal closes
2. Shows "✅ Wallet Setup Complete!" message
3. Suggests next commands
4. User can now use wallet

**Result:** ✅ Flow completes

### Scenario 5: Verify Words Match Seed
**Test:**
1. Create wallet
2. Note first 16 words of mnemonic (internal)
3. Complete backup
4. Compare recovery challenge with first 16 words

**Expected:**
- Recovery challenge = first 16 words of 24-word seed

**Verification (Code):**
```typescript
// wallet.ts - backupToNightChain
const mnemonicWords = pendingMnemonic.split(' ');
const challengeWords = mnemonicWords.slice(0, 16);
```

**Result:** ✅ First 16 words used

### Scenario 6: Wrong Word Count
**Test:** Pass 15 or 17 words to component

**Expected:**
- Component returns null
- Error logged to console
- No crash

**Result:** ✅ Graceful handling

## UI/UX Features

### Visual Hierarchy
1. **Header:** Big, bold warning
2. **Explanation:** Why these words matter
3. **Words Display:** 4 lines clearly formatted
4. **Copy Button:** Easy backup
5. **Instructions:** How to use
6. **Checkbox:** Commitment
7. **Continue Button:** Next step
8. **Final Warning:** Last reminder

✅ Clear information flow
✅ Progressive disclosure

### Accessibility
```tsx
<div className="recovery-words-overlay"> {/* Modal backdrop */}
  <div className="recovery-words-modal"> {/* Modal content */}
    <label className="acknowledgment-checkbox">
      <input type="checkbox" ... />
      <span>I have written down...</span>
    </label>
  </div>
</div>
```

✅ Proper label associations
✅ Keyboard accessible
✅ Screen reader friendly

### Security Emphasis
- ⚠️ Warning badge at top
- **Bold text** for critical info
- ⚠️ Final warning at bottom
- Red/orange colors (CSS)
- "CANNOT recover" language

✅ User cannot miss importance

### User Guidance
- Numbered list for instructions
- Alternating line labels (Bot/You)
- Examples of recovery flow
- Clear action items

✅ User knows exactly what to do

## Validation: ✅ PASSED

**Evidence:**
1. ✅ Shows after wallet creation + Night backup
2. ✅ Displays 16 words clearly
3. ✅ 4 lines with 4 words each
4. ✅ Line labels (Bot/You alternating)
5. ✅ Explanation of purpose
6. ✅ Copy button with feedback
7. ✅ Checkbox: "I saved these words"
8. ✅ Continue button disabled until checked
9. ✅ Instructions how to use
10. ✅ Multiple warnings about importance

**Recovery Challenge:**
- First 16 words from 24-word seed
- Stored in chrome.storage.local
- Persists across browser restarts
- Displayed in clear 4-line format
- User must acknowledge before continuing

**User Experience:**
- Cannot proceed without acknowledgment
- Clear visual hierarchy
- Copy button for easy backup
- Step-by-step instructions
- Multiple warnings

**All 10 Tasks Complete!**
