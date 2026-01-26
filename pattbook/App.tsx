import { StatusBar } from 'expo-status-bar';
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { View, Text } from 'react-native';

import RoleSelection from './src/components/RoleSelection';
import RetailerHome from './src/components/RetailerHome';
import CustomerHomeView from './src/components/CustomerHome';
import OTPAuth from './src/components/OTPAuth';

const Stack = createStackNavigator();
const ROLE_STORAGE_KEY = '@pattbook_user_role';

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="auto" />
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen name="RoleSelection" component={RoleSelection} />
        <Stack.Screen name="OTPAuth" component={OTPAuth} />
        <Stack.Screen name="RetailerHome" component={RetailerHome} />
        <Stack.Screen name="CustomerHome" component={CustomerHomeView} />
        
        {/* Retailer Screens */}
        <Stack.Screen name="AddCustomerManual" component={AddCustomerManual} />
        <Stack.Screen name="DebtorDetails" component={DebtorDetails} />
        <Stack.Screen name="CollectedPayment" component={CollectedPayment} />
        <Stack.Screen name="Settings" component={Settings} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

// Placeholder components for navigation (to be implemented)
const AddCustomerManual = () => {
  return <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}><Text>Add Customer Manual</Text></View>;
};

const DebtorDetails = () => {
  return <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}><Text>Debtor Details</Text></View>;
};

const CollectedPayment = () => {
  return <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}><Text>Collected Payment</Text></View>;
};

const Settings = () => {
  return <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}><Text>Settings</Text></View>;
};
