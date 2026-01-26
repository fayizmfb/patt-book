import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  Image,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as Location from 'expo-location';
import axios from 'axios';
import { useNavigation } from '@react-navigation/native';
import { API_CONFIG, buildApiUrl } from '../config/api';

const RetailerAccountCreation = ({ route }: any) => {
  const { mobileNumber, userRole } = route.params;
  const navigation = useNavigation();

  const [formData, setFormData] = useState({
    shopName: '',
    shopAddress: '',
    shopPhotoUrl: '',
    latitude: null as number | null,
    longitude: null as number | null,
  });

  const [isLoading, setIsLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState(false);

  useEffect(() => {
    requestLocationPermission();
  }, []);

  const requestLocationPermission = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert(
          'Permission Required',
          'Location permission is required to auto-detect your shop address. Please enable it in settings.',
          [{ text: 'OK' }]
        );
      }
    } catch (error) {
      console.error('Location permission error:', error);
    }
  };

  const getCurrentLocation = async () => {
    setLocationLoading(true);
    try {
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });

      const { latitude, longitude } = location.coords;
      
      // Reverse geocoding to get address (you can use a geocoding API)
      const address = await getAddressFromCoords(latitude, longitude);
      
      setFormData(prev => ({
        ...prev,
        latitude,
        longitude,
        shopAddress: address,
      }));

      Alert.alert('Location Detected', 'Your shop address has been auto-detected. Please confirm or edit it.');
    } catch (error) {
      console.error('Location error:', error);
      Alert.alert('Error', 'Failed to detect location. Please enter address manually.');
    } finally {
      setLocationLoading(false);
    }
  };

  const getAddressFromCoords = async (lat: number, lng: number): Promise<string> => {
    // Mock address for now - in production, use geocoding API
    return `Auto-detected address for coordinates ${lat.toFixed(6)}, ${lng.toFixed(6)}`;
  };

  const pickImage = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.7,
      });

      if (!result.canceled && result.assets[0]) {
        setFormData(prev => ({
          ...prev,
          shopPhotoUrl: result.assets[0].uri,
        }));
      }
    } catch (error) {
      console.error('Image picker error:', error);
      Alert.alert('Error', 'Failed to pick image. Please try again.');
    }
  };

  const takePhoto = async () => {
    try {
      const result = await ImagePicker.launchCameraAsync({
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.7,
      });

      if (!result.canceled && result.assets[0]) {
        setFormData(prev => ({
          ...prev,
          shopPhotoUrl: result.assets[0].uri,
        }));
      }
    } catch (error) {
      console.error('Camera error:', error);
      Alert.alert('Error', 'Failed to take photo. Please try again.');
    }
  };

  const validateForm = () => {
    const requiredFields = ['shopName', 'shopAddress', 'shopPhotoUrl'];
    const missingFields = requiredFields.filter(field => !formData[field as keyof typeof formData]);

    if (missingFields.length > 0) {
      Alert.alert('Missing Information', 'Please fill in all required fields.');
      return false;
    }

    if (!formData.latitude || !formData.longitude) {
      Alert.alert('Location Required', 'Please detect your location or enter coordinates manually.');
      return false;
    }

    return true;
  };

  const createAccount = async () => {
    if (!validateForm()) return;

    setIsLoading(true);
    try {
      const response = await axios.post(buildApiUrl(API_CONFIG.ENDPOINTS.CREATE_ACCOUNT), {
        mobile_number: mobileNumber,
        user_type: userRole,
        shop_name: formData.shopName,
        shop_address: formData.shopAddress,
        shop_photo_url: formData.shopPhotoUrl,
        latitude: formData.latitude,
        longitude: formData.longitude,
      });

      if (response.data.success) {
        // Store user data and token
        await AsyncStorage.setItem('@pattbook_user_token', response.data.token);
        await AsyncStorage.setItem('@pattbook_user_data', JSON.stringify(response.data.user));

        Alert.alert('Success', 'Your retailer account has been created successfully!', [
          {
            text: 'OK',
            onPress: () => navigation.replace('RetailerHome'),
          },
        ]);
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
      <ScrollView style={styles.scrollView}>
        <View style={styles.content}>
          <View style={styles.header}>
            <Text style={styles.title}>Create Retailer Account</Text>
            <Text style={styles.subtitle}>Complete your shop details</Text>
          </View>

          <View style={styles.form}>
            {/* Shop Name */}
            <Text style={styles.label}>Shop Name *</Text>
            <TextInput
              style={styles.input}
              placeholder="Enter your shop name"
              value={formData.shopName}
              onChangeText={(text) => setFormData(prev => ({ ...prev, shopName: text }))}
            />

            {/* Shop Address */}
            <Text style={styles.label}>Shop Address *</Text>
            <View style={styles.addressContainer}>
              <TextInput
                style={[styles.input, styles.addressInput]}
                placeholder="Enter your shop address"
                value={formData.shopAddress}
                onChangeText={(text) => setFormData(prev => ({ ...prev, shopAddress: text }))}
                multiline
                numberOfLines={3}
              />
              <TouchableOpacity
                style={[styles.locationButton, locationLoading && styles.disabledButton]}
                onPress={getCurrentLocation}
                disabled={locationLoading}
              >
                <Text style={styles.locationButtonText}>
                  {locationLoading ? 'Detecting...' : '📍 Auto-Detect Location'}
                </Text>
              </TouchableOpacity>
            </View>

            {/* Shop Photo */}
            <Text style={styles.label}>Shop Photo *</Text>
            <View style={styles.photoContainer}>
              {formData.shopPhotoUrl ? (
                <View style={styles.photoPreview}>
                  <Image source={{ uri: formData.shopPhotoUrl }} style={styles.photo} />
                  <TouchableOpacity
                    style={styles.changePhotoButton}
                    onPress={() => {
                      Alert.alert(
                        'Change Photo',
                        'Choose an option',
                        [
                          { text: 'Camera', onPress: takePhoto },
                          { text: 'Gallery', onPress: pickImage },
                          { text: 'Cancel', style: 'cancel' },
                        ]
                      );
                    }}
                  >
                    <Text style={styles.changePhotoText}>Change Photo</Text>
                  </TouchableOpacity>
                </View>
              ) : (
                <View style={styles.photoPlaceholder}>
                  <Text style={styles.photoPlaceholderText}>📷 Shop Photo</Text>
                  <View style={styles.photoButtons}>
                    <TouchableOpacity
                      style={[styles.photoButton, styles.cameraButton]}
                      onPress={takePhoto}
                    >
                      <Text style={styles.photoButtonText}>Camera</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={[styles.photoButton, styles.galleryButton]}
                      onPress={pickImage}
                    >
                      <Text style={styles.photoButtonText}>Gallery</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              )}
            </View>

            {/* Location Display */}
            {formData.latitude && formData.longitude && (
              <View style={styles.locationDisplay}>
                <Text style={styles.locationDisplayText}>
                  📍 Location: {formData.latitude.toFixed(6)}, {formData.longitude.toFixed(6)}
                </Text>
              </View>
            )}

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
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  scrollView: {
    flex: 1,
  },
  content: {
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
    marginBottom: 20,
    backgroundColor: '#f8f9fa',
  },
  addressContainer: {
    marginBottom: 20,
  },
  addressInput: {
    height: 80,
    textAlignVertical: 'top',
  },
  locationButton: {
    backgroundColor: '#3498db',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },
  disabledButton: {
    backgroundColor: '#bdc3c7',
  },
  locationButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
  },
  photoContainer: {
    marginBottom: 20,
  },
  photoPreview: {
    alignItems: 'center',
  },
  photo: {
    width: 120,
    height: 120,
    borderRadius: 60,
    marginBottom: 12,
  },
  changePhotoButton: {
    backgroundColor: '#e74c3c',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
  },
  changePhotoText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '600',
  },
  photoPlaceholder: {
    alignItems: 'center',
    padding: 20,
    borderWidth: 2,
    borderColor: '#ddd',
    borderStyle: 'dashed',
    borderRadius: 12,
  },
  photoPlaceholderText: {
    fontSize: 16,
    color: '#7f8c8d',
    marginBottom: 16,
  },
  photoButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  photoButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 6,
  },
  cameraButton: {
    backgroundColor: '#3498db',
  },
  galleryButton: {
    backgroundColor: '#2ecc71',
  },
  photoButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
  },
  locationDisplay: {
    backgroundColor: '#ecf0f1',
    padding: 12,
    borderRadius: 8,
    marginBottom: 20,
  },
  locationDisplayText: {
    fontSize: 12,
    color: '#2c3e50',
    textAlign: 'center',
  },
  button: {
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
  },
  createButton: {
    backgroundColor: '#2ecc71',
  },
  buttonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
  },
});

export default RetailerAccountCreation;
