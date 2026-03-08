/**
 * Main chat interface for mobile app
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  TextInput,
  FlatList,
  TouchableOpacity,
  Text,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { CommandParser, ParsedCommand } from '@wallet-ui/shared';
import { useWalletStore } from '../store/wallet';
import { ChatMessage } from '../components/ChatMessage';
import { TransactionPreviewCard } from '../components/TransactionPreviewCard';
import { QuickActions } from '../components/QuickActions';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  preview?: any;
}

export const ChatScreen: React.FC = ({ navigation }: any) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const flatListRef = useRef<FlatList>(null);
  const parser = useRef(new CommandParser());

  const { walletState, processCommand } = useWalletStore();

  useEffect(() => {
    // Welcome message
    if (!walletState.isInitialized) {
      addAssistantMessage(
        "👋 Welcome! Let's get started by setting up your wallet."
      );
    } else {
      addAssistantMessage(
        `Welcome back! You have ${walletState.assets.length} assets. What would you like to do?`
      );
    }
  }, []);

  const addAssistantMessage = (content: string, preview?: any) => {
    setMessages(prev => [
      ...prev,
      {
        id: Date.now().toString(),
        role: 'assistant',
        content,
        timestamp: Date.now(),
        preview,
      },
    ]);
  };

  const handleSubmit = async () => {
    if (!input.trim() || isProcessing) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsProcessing(true);

    try {
      const parsed = parser.current.parse(userMessage.content);

      if (parsed.ambiguities.length > 0) {
        const ambiguityMessage = parsed.ambiguities
          .map(a => `• ${a.message}`)
          .join('\n');
        addAssistantMessage(ambiguityMessage);
        setIsProcessing(false);
        return;
      }

      const response = await processCommand(parsed);

      if (response.requiresConfirmation && response.preview) {
        addAssistantMessage('Please review this transaction:', response.preview);
      } else {
        addAssistantMessage(response.message);
      }
    } catch (error: any) {
      addAssistantMessage(`❌ ${error.message || 'Something went wrong'}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleQuickAction = (command: string) => {
    setInput(command);
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={90}
    >
      {/* Messages */}
      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={item => item.id}
        renderItem={({ item }) => (
          <>
            <ChatMessage message={item} />
            {item.preview && (
              <TransactionPreviewCard
                preview={item.preview}
                onConfirm={() => addAssistantMessage('✅ Transaction submitted!')}
                onEdit={() => addAssistantMessage('What would you like to change?')}
                onCancel={() => addAssistantMessage('Transaction cancelled.')}
              />
            )}
          </>
        )}
        contentContainerStyle={styles.messagesList}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd()}
      />

      {/* Loading */}
      {isProcessing && (
        <View style={styles.loadingContainer}>
          <ActivityIndicator color="#667eea" />
          <Text style={styles.loadingText}>Processing...</Text>
        </View>
      )}

      {/* Quick Actions */}
      <QuickActions onAction={handleQuickAction} disabled={isProcessing} />

      {/* Input */}
      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="Type a command... e.g., send 10 ADA to $alice"
          placeholderTextColor="#999"
          multiline
          editable={!isProcessing && !walletState.isLocked}
          accessible={true}
          accessibilityLabel="Command input"
          accessibilityHint="Enter natural language commands like 'send 10 ADA to address'"
        />
        <TouchableOpacity
          style={[styles.sendButton, (!input.trim() || isProcessing) && styles.sendButtonDisabled]}
          onPress={handleSubmit}
          disabled={!input.trim() || isProcessing}
          accessible={true}
          accessibilityLabel="Send command"
          accessibilityRole="button"
        >
          <Text style={styles.sendButtonText}>
            {isProcessing ? '⏳' : '➤'}
          </Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f7fa',
  },
  messagesList: {
    padding: 16,
  },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    backgroundColor: 'white',
    marginHorizontal: 16,
    borderRadius: 8,
    marginBottom: 8,
  },
  loadingText: {
    marginLeft: 8,
    color: '#718096',
    fontSize: 13,
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderTopColor: '#e1e8ed',
    alignItems: 'flex-end',
  },
  input: {
    flex: 1,
    backgroundColor: '#f7fafc',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 15,
    maxHeight: 100,
    borderWidth: 1,
    borderColor: '#e1e8ed',
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#667eea',
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },
  sendButtonDisabled: {
    backgroundColor: '#cbd5e0',
  },
  sendButtonText: {
    fontSize: 20,
    color: 'white',
  },
});
