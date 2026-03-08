/**
 * Mobile app entry point
 */

import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { ChatScreen } from './src/screens/ChatScreen';
import { WalletSetupScreen } from './src/screens/WalletSetupScreen';
import { SettingsScreen } from './src/screens/SettingsScreen';
import { AssetsScreen } from './src/screens/AssetsScreen';
import { TransactionHistoryScreen } from './src/screens/TransactionHistoryScreen';

const Stack = createStackNavigator();

export default function App() {
  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <Stack.Navigator
          initialRouteName="Chat"
          screenOptions={{
            headerStyle: {
              backgroundColor: '#667eea',
            },
            headerTintColor: '#fff',
            headerTitleStyle: {
              fontWeight: '600',
            },
          }}
        >
          <Stack.Screen
            name="Chat"
            component={ChatScreen}
            options={{ title: '💬 Wallet Chat' }}
          />
          <Stack.Screen
            name="WalletSetup"
            component={WalletSetupScreen}
            options={{ title: 'Setup Wallet' }}
          />
          <Stack.Screen
            name="Assets"
            component={AssetsScreen}
            options={{ title: 'Your Assets' }}
          />
          <Stack.Screen
            name="History"
            component={TransactionHistoryScreen}
            options={{ title: 'Transaction History' }}
          />
          <Stack.Screen
            name="Settings"
            component={SettingsScreen}
            options={{ title: 'Settings' }}
          />
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
