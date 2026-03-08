import React from 'react';
import { formatRelativeTime } from '@wallet-ui/shared';
import './ChatMessage.css';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'wali';
  content: string;
  timestamp: number;
}

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const displayRole = isUser ? 'You' : 'wAli';
  const avatarEmoji = isUser ? '👤' : null;
  const avatarImg = !isUser ? 'assets/icon-48.png' : null;

  return (
    <div
      className={`chat-message ${isUser ? 'user-message' : 'assistant-message'}`}
      role="article"
      aria-label={`${displayRole} said: ${message.content}`}
    >
      <div className="message-avatar" aria-hidden="true">
        {avatarEmoji && avatarEmoji}
        {avatarImg && <img src={avatarImg} alt="wAli" style={{width: '24px', height: '24px', borderRadius: '50%'}} />}
      </div>
      <div className="message-content">
        <div className="message-text">{message.content}</div>
        <time
          className="message-time"
          dateTime={new Date(message.timestamp).toISOString()}
          aria-label={`Sent ${formatRelativeTime(message.timestamp)}`}
        >
          {formatRelativeTime(message.timestamp)}
        </time>
      </div>
    </div>
  );
};
