"""
Firebase Configuration and Authentication Helper
Handles Firebase Auth (Phone OTP) and Firestore database operations
"""

import os
from flask import session

# Firebase configuration - Replace with your Firebase project credentials
# Get these from Firebase Console > Project Settings > General > Your apps
FIREBASE_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY", "your-api-key-here"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", "your-project.firebaseapp.com"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID", "your-project-id"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", "your-project.appspot.com"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", "123456789"),
    "appId": os.getenv("FIREBASE_APP_ID", "your-app-id"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL", "")  # Optional, for Realtime Database
}

# Initialize Firebase (disabled for compatibility - using simplified authentication mode)
FIREBASE_AVAILABLE = False
auth = None
db = None
print("Using simplified authentication mode (Firebase disabled for Python 3.14 compatibility).")


def verify_phone_otp(phone_number, verification_code):
    """
    Verify phone OTP code with Firebase Authentication
    
    Args:
        phone_number: User's phone number (with country code, e.g., +1234567890)
        verification_code: OTP code sent to user's phone
    
    Returns:
        dict: User data if successful, None if failed
    """
    try:
        # Firebase phone auth verification
        # Note: This is a simplified approach. In production, you'd handle the verification flow properly
        # Firebase Phone Auth requires a verification ID first, then code verification
        # For simplicity, we're using a basic approach here
        
        # In actual implementation, you need to:
        # 1. Send verification code: auth.send_phone_verification_code(phone_number)
        # 2. Verify code: auth.verify_phone_code(verification_id, verification_code)
        
        # This is a placeholder - you'll need to implement proper Firebase Phone Auth flow
        # See Firebase documentation for complete implementation
        
        return None
    except Exception as e:
        print(f"Error verifying phone OTP: {str(e)}")
        return None


def get_user_store_data(user_id):
    """
    Get store data for authenticated user from Firestore/Realtime Database
    
    Args:
        user_id: Firebase user ID
    
    Returns:
        dict: Store data (store_name, store_address) if exists, None otherwise
    """
    if not FIREBASE_AVAILABLE:
        # Simplified mode: Check session storage
        return session.get('store_data', None)
    
    try:
        # Using Realtime Database
        user_data = db.child("stores").child(user_id).get().val()
        return user_data
    except Exception as e:
        print(f"Error getting user store data: {str(e)}")
        return None


def save_user_store_data(user_id, phone_number, store_name, store_address):
    """
    Save store data for authenticated user to Firestore/Realtime Database
    
    Args:
        user_id: Firebase user ID
        phone_number: User's phone number
        store_name: Store name
        store_address: Store address
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not FIREBASE_AVAILABLE:
        # Simplified mode: Store in session
        session['store_data'] = {
            "phone_number": phone_number,
            "store_name": store_name,
            "store_address": store_address
        }
        return True
    
    try:
        # Save to Realtime Database
        from datetime import datetime
        store_data = {
            "phone_number": phone_number,
            "store_name": store_name,
            "store_address": store_address,
            "created_at": datetime.now().isoformat()
        }
        db.child("stores").child(user_id).set(store_data)
        return True
    except Exception as e:
        print(f"Error saving user store data: {str(e)}")
        return False


def is_user_logged_in():
    """
    Check if user is logged in (has valid session)
    
    Returns:
        bool: True if logged in, False otherwise
    """
    return 'user_id' in session and 'phone_number' in session


def get_current_user_id():
    """
    Get current logged-in user ID from session
    
    Returns:
        str: User ID if logged in, None otherwise
    """
    return session.get('user_id', None)


def get_current_user_phone():
    """
    Get current logged-in user phone number from session
    
    Returns:
        str: Phone number if logged in, None otherwise
    """
    return session.get('phone_number', None)

