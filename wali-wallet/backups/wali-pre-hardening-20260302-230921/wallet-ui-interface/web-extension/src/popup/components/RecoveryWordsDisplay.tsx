/**
 * Night Chain 4-Line Recovery Challenge Display
 * Shows the 16-word recovery challenge after wallet backup
 */

import React, { useState } from 'react';
import './RecoveryWordsDisplay.css';

interface RecoveryWordsDisplayProps {
  challengeWords: string[]; // 16 words total
  onAcknowledge: () => void;
}

export const RecoveryWordsDisplay: React.FC<RecoveryWordsDisplayProps> = ({
  challengeWords,
  onAcknowledge,
}) => {
  const [copied, setCopied] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);

  if (challengeWords.length !== 16) {
    console.error('Expected 16 challenge words, got:', challengeWords.length);
    return null;
  }

  // Split into 4 lines of 4 words each
  const lines = [
    challengeWords.slice(0, 4),   // Line 1 (Bot)
    challengeWords.slice(4, 8),   // Line 2 (You)
    challengeWords.slice(8, 12),  // Line 3 (Bot)
    challengeWords.slice(12, 16), // Line 4 (You)
  ];

  const lineLabels = ['Bot', 'You', 'Bot', 'You'];

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

  const handleAcknowledge = () => {
    if (!acknowledged) {
      alert('Please make sure you have saved these words before continuing!');
      return;
    }
    onAcknowledge();
  };

  return (
    <div className="recovery-words-overlay">
      <div className="recovery-words-modal">
        <div className="recovery-header">
          <h2>🦭 SAVE THESE RECOVERY WORDS!</h2>
          <div className="warning-badge">⚠️ Critical - Write These Down!</div>
        </div>

        <div className="recovery-explanation">
          <p>
            <strong>If you forget your access key, these 16 words are your ONLY way to recover your wallet!</strong>
          </p>
          <p>
            Write them down exactly as shown below. Keep them safe and private.
          </p>
        </div>

        {/* 4-Line Challenge Display */}
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

        {/* Copy Button */}
        <button
          className="copy-recovery-btn"
          onClick={handleCopyAll}
          disabled={copied}
        >
          {copied ? '✅ Copied to Clipboard!' : '📋 Copy All Words'}
        </button>

        {/* Recovery Instructions */}
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

        {/* Acknowledgment Checkbox */}
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

        {/* Continue Button */}
        <button
          className="continue-btn"
          onClick={handleAcknowledge}
          disabled={!acknowledged}
        >
          I've Saved My Recovery Words - Continue
        </button>

        <div className="final-warning">
          ⚠️ Without these words AND your access key, you CANNOT recover your wallet!
        </div>
      </div>
    </div>
  );
};
