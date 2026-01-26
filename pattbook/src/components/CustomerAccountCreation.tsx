import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { useNavigation } from '@react-navigation/native';

const CustomerAccountCreation = ({ route }: any) => {
  const { mobileNumber, userRole } = route.params;
  const navigation = useNavigation();

  const [customerName, setCustomerName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const API_BASE_URL = 'http://localhost:5000/api';

  const validateForm = () => {
    if (!customerName || customerName.trim().length < 2) {
      Alert.alert('Invalid Name', 'Please enter a valid customer name (at least 2 characters).');
      return false;
    }

    if (customerName.length > 50) {
      Alert.alert('Invalid Name', 'Customer name should not exceed 50 characters.');
      return false;
    }

    return true;
  };

  const createAccount = async () => {
    if (!validateForm()) return;

    setIsLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/create-account`, {
        mobile_number: mobileNumber,
        user_type: userRole,
        customer_name: customerName.trim(),
      });

      if (response.data.success) {
        // Store user data and token
        await AsyncStorage.setItem('@pattbook_user_token', response.data.token);
        await AsyncStorage.setItem('@pattbook_user_data', JSON.stringify(response.data.user));

        Alert.alert(
          'Success',
          'Your customer account has been created successfully!',
          [
            {
              text: 'OK',
              onPress: () => navigation.replace('CustomerHome'),
            },
          ]
        );
      } else {
        Alert.alert('Error', response.data.message || 'Failed to create account');
      }
    } catch (error: any) {
      console.error('Account creation error:', error);
      Alert.alert('Error', 'Failed to create account. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container} 
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Create Customer Account</Text>
          <Text style={styles.subtitle}>Enter your details to get started</Text>
        </View>

        <View style={styles.form}>
          {/* Mobile Number Display */}
          <View style={styles.mobileDisplay}>
            <Text style={styles.mobileLabel}>Mobile Number</Text>
            <Text style={styles.mobileNumber}>+91 {mobileNumber}</Text>
          </View>

          {/* Customer Name */}
          <Text style={styles.label}>Your Name *</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter your full name"
            value={customerName}
            onChangeText={setCustomerName}
            maxLength={50}
            autoFocus
          />

          <Text style={styles.helperText}>
            This name will be displayed to retailers when you make purchases
          </Text>

          {/* Create Account Button */}
          <TouchableOpacity
            style={[styles.button, styles.createButton, isLoading && styles.disabledButton]}
            onPress={createAccount}
            disabled={isLoading}
          >
            <Text style={styles.buttonText}>
              {isLoading ? 'Creating Account...' : 'Create Account'}
            </Text>
          </TouchableOpacity>

          {/* Terms Note */}
          <View style={styles.termsContainer}>
            <Text style={styles.termsText}>
              By creating an account, you agree to receive payment reminders via WhatsApp
            </Text>
          </View>
        </View>

        {/* Benefits */}
        <View style={styles.benefits}>
          <Text style={styles.benefitsTitle}>Why Patt Book?</Text>
          <View style={styles.benefitItem}>
            <Text style={styles.benefitIcon}>✓</Text>
            <Text style={styles.benefitText}>Track all your dues in one place</Text>
          </View>
          <View style={styles.benefitItem}>
            <Text style={styles.benefitIcon}>✓</Text>
            <Text style={styles.benefitText}>Get WhatsApp reminders for pending payments</Text>
          </View>
          <View style={styles.benefitItem}>
            <Text style={styles.benefitIcon}>✓</Text>
            <Text style={styles.benefitText}>View complete transaction history</Text>
          </View>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  content: {
    flex: 1,
    padding: 20,
  },
  header: {
    alignItems: 'center',
    marginBottom: 30,
    marginTop: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#7f8c8d',
    textAlign: 'center',
  },
  form: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
    marginBottom: 20,
  },
  mobileDisplay: {
    backgroundColor: '#ecf0f1',
    padding: 16,
    borderRadius: 8,
    marginBottom: 20,
  },
  mobileLabel: {
    fontSize: 12,
    color: '#7f8c8d',
    marginBottom: 4,
  },
  mobileNumber: {
    fontSize: 18,
    fontWeight: '600',
    color: '#2c3e50',
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 16,
    fontSize: 16,
    marginBottom: 8,
    backgroundColor: '#f8f9fa',
  },
  helperText: {
    fontSize: 12,
    color: '#7f8c8d',
    marginBottom: 20,
    textAlign: 'center',
  },
  button: {
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    marginBottom: 16,
  },
  createButton: {
    backgroundColor: '#3498db',
  },
  disabledButton: {
    backgroundColor: '#bdc3c7',
  },
  buttonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
  },
  termsContainer: {
    alignItems: 'center',
  },
  termsText: {
    fontSize: 12,
    color: '#95a5a6',
    textAlign: 'center',
    lineHeight: 18,
  },
  benefits: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  benefitsTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 16,
    textAlign: 'center',
  },
  benefitItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  benefitIcon: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2ecc71',
    marginRight: 12,
    width: 20,
  },
  benefitText: {
    fontSize: 14,
    color: '#2c3e50',
    flex: 1,
  },
});

export default CustomerAccountCreation;
