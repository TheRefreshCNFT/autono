/**
 * Night Chain Recovery Import Modal
 * 4-line challenge input for wallet recovery
 */

import React, { useState } from 'react';
import './RecoveryImportModal.css';

interface RecoveryImportModalProps {
  onRecover: (challengeWords: string[], accessKey: string) => Promise<void>;
  onCancel: () => void;
}

export const RecoveryImportModal: React.FC<RecoveryImportModalProps> = ({
  onRecover,
  onCancel,
}) => {
  const [line1, setLine1] = useState('');
  const [line2, setLine2] = useState('');
  const [line3, setLine3] = useState('');
  const [line4, setLine4] = useState('');
  const [accessKey, setAccessKey] = useState('');
  const [isRecovering, setIsRecovering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate all lines have 4 words
    const lines = [line1, line2, line3, line4];
    for (let i = 0; i < lines.length; i++) {
      const words = lines[i].trim().split(/\s+/);
      if (words.length !== 4) {
        setError(`Line ${i + 1} must have exactly 4 words (you entered ${words.length})`);
        return;
      }
    }

    // Validate access key
    if (!accessKey || accessKey.length < 4 || accessKey.length > 12) {
      setError('Access key must be 4-12 characters');
      return;
    }

    // Combine all words
    const allWords = [
      ...line1.trim().split(/\s+/),
      ...line2.trim().split(/\s+/),
      ...line3.trim().split(/\s+/),
      ...line4.trim().split(/\s+/),
    ];

    setIsRecovering(true);

    try {
      await onRecover(allWords, accessKey);
    } catch (err: any) {
      setError(err.message || 'Recovery failed');
      setIsRecovering(false);
    }
  };

  return (
    <div className="recovery-import-overlay">
      <div className="recovery-import-modal">
        <div className="modal-header">
          <h2>🦭 Recover from Night Chain</h2>
          <button className="close-btn" onClick={onCancel} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="recovery-intro">
          <p>
            Enter the 4 lines of recovery words you saved when you created your wallet.
          </p>
          <p>
            The pattern alternates: <strong>Bot → You → Bot → You</strong>
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Line 1 (Bot) */}
          <div className="recovery-line">
            <label className="line-label bot">
              <span className="line-number">Line 1</span>
              <span className="line-actor">(Bot)</span>
            </label>
            <input
              type="text"
              className="line-input"
              placeholder="word1 word2 word3 word4"
              value={line1}
              onChange={(e) => setLine1(e.target.value)}
              required
              disabled={isRecovering}
            />
          </div>

          {/* Line 2 (You) */}
          <div className="recovery-line">
            <label className="line-label you">
              <span className="line-number">Line 2</span>
              <span className="line-actor">(You)</span>
            </label>
            <input
              type="text"
              className="line-input"
              placeholder="word5 word6 word7 word8"
              value={line2}
              onChange={(e) => setLine2(e.target.value)}
              required
              disabled={isRecovering}
            />
          </div>

          {/* Line 3 (Bot) */}
          <div className="recovery-line">
            <label className="line-label bot">
              <span className="line-number">Line 3</span>
              <span className="line-actor">(Bot)</span>
            </label>
            <input
              type="text"
              className="line-input"
              placeholder="word9 word10 word11 word12"
              value={line3}
              onChange={(e) => setLine3(e.target.value)}
              required
              disabled={isRecovering}
            />
          </div>

          {/* Line 4 (You) */}
          <div className="recovery-line">
            <label className="line-label you">
              <span className="line-number">Line 4</span>
              <span className="line-actor">(You)</span>
            </label>
            <input
              type="text"
              className="line-input"
              placeholder="word13 word14 word15 word16"
              value={line4}
              onChange={(e) => setLine4(e.target.value)}
              required
              disabled={isRecovering}
            />
          </div>

          {/* Access Key */}
          <div className="access-key-section">
            <label className="access-key-label">
              Access Key (4-12 characters)
            </label>
            <input
              type="password"
              className="access-key-input"
              placeholder="Enter your access key"
              value={accessKey}
              onChange={(e) => setAccessKey(e.target.value)}
              required
              minLength={4}
              maxLength={12}
              disabled={isRecovering}
            />
            <p className="access-key-hint">
              This is the key you created when you first backed up your wallet
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="error-message">
              ❌ {error}
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            className="recover-btn"
            disabled={isRecovering}
          >
            {isRecovering ? '🔄 Recovering...' : '🔓 Recover Wallet'}
          </button>

          {/* Cancel Button */}
          <button
            type="button"
            className="cancel-btn"
            onClick={onCancel}
            disabled={isRecovering}
          >
            Cancel
          </button>
        </form>

        <div className="recovery-help">
          <h4>Need Help?</h4>
          <ul>
            <li>Make sure each line has exactly 4 words</li>
            <li>Check spelling - words must match exactly</li>
            <li>The pattern is: Bot, You, Bot, You</li>
            <li>Your access key is case-sensitive</li>
          </ul>
        </div>
      </div>
    </div>
  );
};
