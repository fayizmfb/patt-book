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

# Initialize Firebase
try:
    import firebase_admin
    from firebase_admin import credentials, auth as admin_auth, db as admin_db
    
    # Check if we have credentials to initialize
    if not firebase_admin._apps:
        # Use Application Default Credentials (ADC) or service account if available
        # logic: try to find serviceAccountKey.json, else rely on ADC
        if os.path.exists('serviceAccountKey.json'):
            cred = credentials.Certificate('serviceAccountKey.json')
            firebase_admin.initialize_app(cred, {
                'databaseURL': FIREBASE_CONFIG['databaseURL'],
                'storageBucket': FIREBASE_CONFIG['storageBucket']
            })
        else:
             firebase_admin.initialize_app()

    FIREBASE_AVAILABLE = True
    auth = admin_auth
    db = admin_db
    print("Firebase initialized successfully.")
except Exception as e:
    FIREBASE_AVAILABLE = False
    auth = None
    db = None
    print(f"Firebase initialization failed: {e}. Using simplified mode.")


def verify_firebase_token(id_token):
    """
    Verify Firebase ID Token from client
    
    Args:
        id_token: The Firebase ID token string
    
    Returns:
        dict: Decoded token claims (uid, phone_number, etc.) if valid, None otherwise
    """
    if not FIREBASE_AVAILABLE:
        return None

    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print(f"Error verifying Firebase ID token: {e}")
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

