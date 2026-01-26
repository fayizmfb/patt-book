import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
} from 'react-native';

const CustomerHome = () => {
  // Mock data for stores where customer has dues
  const stores = [
    {
      id: 1,
      shopName: 'General Store',
      shopPhoto: 'https://via.placeholder.com/60',
      dueAmount: 1500,
      shopAddress: '123 Main St',
    },
    {
      id: 2,
      shopName: 'Electronics Shop',
      shopPhoto: 'https://via.placeholder.com/60',
      dueAmount: 800,
      shopAddress: '456 Park Ave',
    },
  ];

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Patt Book</Text>
        <Text style={styles.headerSubtitle}>Customer Dashboard</Text>
      </View>

      {/* Stores List */}
      <ScrollView style={styles.content}>
        <Text style={styles.sectionTitle}>Your Due Amounts</Text>
        
        {stores.map((store) => (
          <TouchableOpacity key={store.id} style={styles.storeCard}>
            <View style={styles.storeInfo}>
              <Image source={{ uri: store.shopPhoto }} style={styles.storePhoto} />
              <View style={styles.storeDetails}>
                <Text style={styles.storeName}>{store.shopName}</Text>
                <Text style={styles.storeAddress}>{store.shopAddress}</Text>
              </View>
            </View>
            <View style={styles.dueAmount}>
              <Text style={styles.amountText}>₹{store.dueAmount}</Text>
              <Text style={styles.amountLabel}>Due Amount</Text>
            </View>
          </TouchableOpacity>
        ))}
        
        {stores.length === 0 && (
          <View style={styles.noDuesContainer}>
            <Text style={styles.noDuesText}>No pending dues</Text>
            <Text style={styles.noDuesSubtext}>You don't have any outstanding payments</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  header: {
    backgroundColor: '#3498db',
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
  content: {
    flex: 1,
    padding: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 16,
  },
  storeCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
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
  storeInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  storePhoto: {
    width: 60,
    height: 60,
    borderRadius: 30,
    marginRight: 12,
  },
  storeDetails: {
    flex: 1,
  },
  storeName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 4,
  },
  storeAddress: {
    fontSize: 12,
    color: '#7f8c8d',
  },
  dueAmount: {
    alignItems: 'flex-end',
  },
  amountText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#e74c3c',
    marginBottom: 2,
  },
  amountLabel: {
    fontSize: 10,
    color: '#95a5a6',
  },
  noDuesContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  noDuesText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#27ae60',
    marginBottom: 8,
  },
  noDuesSubtext: {
    fontSize: 14,
    color: '#7f8c8d',
    textAlign: 'center',
  },
});

export default CustomerHome;
