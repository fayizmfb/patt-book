import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Image,
  Alert,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useNavigation } from '@react-navigation/native';

const ROLE_STORAGE_KEY = '@pattbook_user_role';

const RoleSelection = () => {
  const [isLoading, setIsLoading] = useState(true);
  const navigation = useNavigation();

  useEffect(() => {
    checkExistingRole();
  }, []);

  const checkExistingRole = async () => {
    try {
      const savedRole = await AsyncStorage.getItem(ROLE_STORAGE_KEY);
      if (savedRole) {
        // Role already selected, navigate to OTP auth
        navigation.replace('OTPAuth', { userRole: savedRole });
      } else {
        setIsLoading(false);
      }
    } catch (error) {
      console.error('Error checking role:', error);
      setIsLoading(false);
    }
  };

  const selectRole = async (role: 'retailer' | 'customer') => {
    try {
      await AsyncStorage.setItem(ROLE_STORAGE_KEY, role);
      
      // Navigate to OTP auth
      navigation.replace('OTPAuth', { userRole: role });
    } catch (error) {
      console.error('Error saving role:', error);
      Alert.alert('Error', 'Failed to save role selection. Please try again.');
    }
  };

  const resetRoleSelection = async () => {
    try {
      await AsyncStorage.removeItem(ROLE_STORAGE_KEY);
      Alert.alert('Success', 'Role selection reset. Please select your role again.');
    } catch (error) {
      console.error('Error resetting role:', error);
      Alert.alert('Error', 'Failed to reset role selection.');
    }
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Patt Book</Text>
        <Text style={styles.subtitle}>Choose Your Role</Text>
      </View>

      <View style={styles.roleContainer}>
        <TouchableOpacity
          style={styles.roleCard}
          onPress={() => selectRole('retailer')}
          activeOpacity={0.8}
        >
          <View style={styles.roleIcon}>
            <Text style={styles.iconText}>🏪</Text>
          </View>
          <Text style={styles.roleTitle}>Retailer</Text>
          <Text style={styles.roleDescription}>
            Manage your store, customers, and payments
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.roleCard}
          onPress={() => selectRole('customer')}
          activeOpacity={0.8}
        >
          <View style={styles.roleIcon}>
            <Text style={styles.iconText}>👤</Text>
          </View>
          <Text style={styles.roleTitle}>Customer</Text>
          <Text style={styles.roleDescription}>
            View your dues and transaction history
          </Text>
        </TouchableOpacity>
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>
          Your selection will be saved for future use
        </Text>
        <TouchableOpacity
          style={styles.resetButton}
          onPress={resetRoleSelection}
        >
          <Text style={styles.resetButtonText}>Reset Role (Testing)</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
    padding: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f8f9fa',
  },
  loadingText: {
    fontSize: 16,
    color: '#666',
  },
  header: {
    alignItems: 'center',
    marginTop: 60,
    marginBottom: 40,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 18,
    color: '#7f8c8d',
  },
  roleContainer: {
    flex: 1,
    justifyContent: 'center',
    gap: 20,
  },
  roleCard: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  roleIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#ecf0f1',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  iconText: {
    fontSize: 40,
  },
  roleTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 8,
  },
  roleDescription: {
    fontSize: 14,
    color: '#7f8c8d',
    textAlign: 'center',
    lineHeight: 20,
  },
  footer: {
    alignItems: 'center',
    paddingBottom: 40,
  },
  footerText: {
    fontSize: 12,
    color: '#95a5a6',
    textAlign: 'center',
    marginBottom: 16,
  },
  resetButton: {
    backgroundColor: '#e74c3c',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  resetButtonText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: 'bold',
  },
});

export default RoleSelection;
