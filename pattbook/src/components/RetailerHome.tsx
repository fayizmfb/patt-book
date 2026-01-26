import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';

const RetailerHome = () => {
  const navigation = useNavigation();

  const handleAddCustomer = () => {
    Alert.alert('Add Customer', 'Choose how to add customer:', [
      {
        text: 'Phone Contacts',
        onPress: () => console.log('Add from contacts'),
      },
      {
        text: 'Manual Entry',
        onPress: () => navigation.navigate('AddCustomerManual'),
      },
      {
        text: 'Cancel',
        style: 'cancel',
      },
    ]);
  };

  const handleDebtorDetails = () => {
    navigation.navigate('DebtorDetails');
  };

  const handleCollectedPayment = () => {
    navigation.navigate('CollectedPayment');
  };

  const handleSettings = () => {
    navigation.navigate('Settings');
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Patt Book</Text>
        <Text style={styles.headerSubtitle}>Retailer Dashboard</Text>
      </View>

      {/* 2x2 Grid */}
      <View style={styles.gridContainer}>
        {/* Row 1 */}
        <View style={styles.row}>
          <TouchableOpacity
            style={styles.box}
            onPress={handleAddCustomer}
            activeOpacity={0.8}
          >
            <View style={styles.iconContainer}>
              <Text style={styles.icon}>➕</Text>
            </View>
            <Text style={styles.boxTitle}>Add Customer</Text>
            <Text style={styles.boxSubtitle}>Phone or Manual</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.box}
            onPress={handleDebtorDetails}
            activeOpacity={0.8}
          >
            <View style={styles.iconContainer}>
              <Text style={styles.icon}>👥</Text>
            </View>
            <Text style={styles.boxTitle}>Debtor Details</Text>
            <Text style={styles.boxSubtitle}>View & Edit</Text>
          </TouchableOpacity>
        </View>

        {/* Row 2 */}
        <View style={styles.row}>
          <TouchableOpacity
            style={styles.box}
            onPress={handleCollectedPayment}
            activeOpacity={0.8}
          >
            <View style={styles.iconContainer}>
              <Text style={styles.icon}>💰</Text>
            </View>
            <Text style={styles.boxTitle}>Collected Payment</Text>
            <Text style={styles.boxSubtitle}>Update Balance</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.box}
            onPress={handleSettings}
            activeOpacity={0.8}
          >
            <View style={styles.iconContainer}>
              <Text style={styles.icon}>⚙️</Text>
            </View>
            <Text style={styles.boxTitle}>Settings</Text>
            <Text style={styles.boxSubtitle}>View Only</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Subscription Plans Banner */}
      <View style={styles.subscriptionBanner}>
        <Text style={styles.bannerTitle}>Subscription Plans</Text>
        <View style={styles.plansContainer}>
          <View style={styles.plan}>
            <Text style={styles.planName}>Silver</Text>
            <Text style={styles.planPrice}>₹399/month</Text>
            <Text style={styles.planFeature}>30 msgs/day</Text>
          </View>
          <View style={styles.plan}>
            <Text style={styles.planName}>Gold</Text>
            <Text style={styles.planPrice}>₹799/month</Text>
            <Text style={styles.planFeature}>60 msgs/day</Text>
          </View>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  header: {
    backgroundColor: '#2c3e50',
    paddingTop: 60,
    paddingBottom: 20,
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#ecf0f1',
  },
  gridContainer: {
    flex: 1,
    padding: 20,
    justifyContent: 'center',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  box: {
    width: '48%',
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 20,
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
  iconContainer: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#ecf0f1',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  icon: {
    fontSize: 30,
  },
  boxTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 4,
    textAlign: 'center',
  },
  boxSubtitle: {
    fontSize: 12,
    color: '#7f8c8d',
    textAlign: 'center',
  },
  subscriptionBanner: {
    backgroundColor: '#3498db',
    padding: 20,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
  },
  bannerTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#ffffff',
    textAlign: 'center',
    marginBottom: 12,
  },
  plansContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  plan: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
    minWidth: 120,
  },
  planName: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 4,
  },
  planPrice: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 4,
  },
  planFeature: {
    fontSize: 12,
    color: '#ecf0f1',
  },
});

export default RetailerHome;
