import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { formatRelativeTime } from '@wallet-ui/shared';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <View
      style={[styles.container, isUser && styles.userContainer]}
      accessible={true}
      accessibilityLabel={`${isUser ? 'You' : 'Assistant'} said: ${message.content}`}
    >
      <View style={[styles.bubble, isUser ? styles.userBubble : styles.assistantBubble]}>
        <Text style={[styles.text, isUser && styles.userText]}>
          {message.content}
        </Text>
        <Text
          style={[styles.timestamp, isUser && styles.userTimestamp]}
          accessible={true}
          accessibilityLabel={`Sent ${formatRelativeTime(message.timestamp)}`}
        >
          {formatRelativeTime(message.timestamp)}
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: 12,
    alignItems: 'flex-start',
  },
  userContainer: {
    alignItems: 'flex-end',
  },
  bubble: {
    maxWidth: '80%',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
  },
  assistantBubble: {
    backgroundColor: 'white',
    borderBottomLeftRadius: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  userBubble: {
    backgroundColor: '#667eea',
    borderBottomRightRadius: 4,
  },
  text: {
    fontSize: 15,
    lineHeight: 22,
    color: '#2d3748',
  },
  userText: {
    color: 'white',
  },
  timestamp: {
    fontSize: 11,
    color: '#718096',
    marginTop: 4,
  },
  userTimestamp: {
    color: 'rgba(255, 255, 255, 0.8)',
    textAlign: 'right',
  },
});
