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
import { useNavigation } from '@react-navigation/native';
import axios from 'axios';
import RetailerAccountCreation from './RetailerAccountCreation';
import CustomerAccountCreation from './CustomerAccountCreation';
import { API_CONFIG, buildApiUrl } from '../config/api';

const OTPAuth = ({ route }: any) => {
  const { userRole } = route.params;
  const [mobileNumber, setMobileNumber] = useState('');
  const [otp, setOtp] = useState('');
  const [isOtpSent, setIsOtpSent] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isNewUser, setIsNewUser] = useState(false);
  const navigation = useNavigation();

  const sendOTP = async () => {
    if (!mobileNumber || mobileNumber.length !== 10) {
      Alert.alert('Error', 'Please enter a valid 10-digit mobile number');
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.post(buildApiUrl(API_CONFIG.ENDPOINTS.SEND_OTP), {
        mobile_number: mobileNumber,
      });

      if (response.data.success) {
        setIsOtpSent(true);
        Alert.alert(
          'OTP Sent',
          response.data.otp 
            ? `Your OTP is: ${response.data.otp} (Testing Mode)`
            : 'OTP has been sent to your WhatsApp number'
        );
      } else {
        Alert.alert('Error', response.data.message || 'Failed to send OTP');
      }
    } catch (error: any) {
      console.error('Send OTP Error:', error);
      Alert.alert('Error', 'Failed to send OTP. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const verifyOTP = async () => {
    if (!otp || otp.length !== 6) {
      Alert.alert('Error', 'Please enter a valid 6-digit OTP');
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.post(buildApiUrl(API_CONFIG.ENDPOINTS.VERIFY_OTP), {
        mobile_number: mobileNumber,
        otp: otp,
        user_type: userRole,
      });

      if (response.data.success) {
        if (response.data.is_new_user) {
          setIsNewUser(true);
          Alert.alert('Account Required', 'Please complete your account creation');
        } else {
          // Existing user - login successful
          await AsyncStorage.setItem('@pattbook_user_token', response.data.token);
          await AsyncStorage.setItem('@pattbook_user_data', JSON.stringify(response.data.user));
          
          // Navigate to appropriate home screen
          if (userRole === 'retailer') {
            navigation.replace('RetailerHome');
          } else {
            navigation.replace('CustomerHome');
          }
        }
      } else {
        Alert.alert('Error', response.data.message || 'Invalid OTP');
      }
    } catch (error: any) {
      console.error('Verify OTP Error:', error);
      Alert.alert('Error', 'Failed to verify OTP. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const resetOTP = () => {
    setIsOtpSent(false);
    setOtp('');
    setIsNewUser(false);
  };

  if (isNewUser) {
    // Navigate to account creation based on user role
    if (userRole === 'retailer') {
      return <RetailerAccountCreation mobileNumber={mobileNumber} userRole={userRole} />;
    } else {
      return <CustomerAccountCreation mobileNumber={mobileNumber} userRole={userRole} />;
    }
  }

  return (
    <KeyboardAvoidingView 
      style={styles.container} 
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Patt Book</Text>
          <Text style={styles.subtitle}>
            {userRole === 'retailer' ? 'Retailer Login' : 'Customer Login'}
          </Text>
        </View>

        {!isOtpSent ? (
          <View style={styles.form}>
            <Text style={styles.label}>Mobile Number</Text>
            <TextInput
              style={styles.input}
              placeholder="Enter 10-digit mobile number"
              value={mobileNumber}
              onChangeText={setMobileNumber}
              keyboardType="phone-pad"
              maxLength={10}
            />

            <TouchableOpacity
              style={[styles.button, styles.primaryButton]}
              onPress={sendOTP}
              disabled={isLoading}
            >
              <Text style={styles.buttonText}>
                {isLoading ? 'Sending...' : 'Send OTP'}
              </Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.form}>
            <View style={styles.mobileDisplay}>
              <Text style={styles.mobileLabel}>Mobile: +91 {mobileNumber}</Text>
              <TouchableOpacity onPress={resetOTP}>
                <Text style={styles.changeText}>Change</Text>
              </TouchableOpacity>
            </View>

            <Text style={styles.label}>Enter OTP</Text>
            <TextInput
              style={styles.input}
              placeholder="Enter 6-digit OTP"
              value={otp}
              onChangeText={setOtp}
              keyboardType="number-pad"
              maxLength={6}
            />

            <TouchableOpacity
              style={[styles.button, styles.primaryButton]}
              onPress={verifyOTP}
              disabled={isLoading}
            >
              <Text style={styles.buttonText}>
                {isLoading ? 'Verifying...' : 'Verify OTP'}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.button, styles.secondaryButton]}
              onPress={sendOTP}
              disabled={isLoading}
            >
              <Text style={[styles.buttonText, styles.secondaryButtonText]}>
                Resend OTP
              </Text>
            </TouchableOpacity>
          </View>
        )}

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            OTP will be sent via WhatsApp from Patt Book number
          </Text>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
});

export default OTPAuth;
