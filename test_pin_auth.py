"""
Test script for PIN Authentication System
Tests the complete flow without WhatsApp dependency
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_check_phone_new_user():
    """Test checking phone number for new user"""
    print("=== Testing Check Phone (New User) ===")
    
    response = requests.post(f"{BASE_URL}/api/auth/check-phone", json={
        "phone": "9876543210"
    })
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_setup_account():
    """Test setting up new account with PIN"""
    print("=== Testing Setup Account ===")
    
    response = requests.post(f"{BASE_URL}/api/auth/setup-account", json={
        "phone": "9876543210",
        "shop_name": "Test Store",
        "shop_address": "123 Test Street, Test City",
        "pin": "1234",
        "confirm_pin": "1234"
    })
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_check_phone_existing_user():
    """Test checking phone number for existing user"""
    print("=== Testing Check Phone (Existing User) ===")
    
    response = requests.post(f"{BASE_URL}/api/auth/check-phone", json={
        "phone": "9876543210"
    })
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_login_with_pin():
    """Test login with correct PIN"""
    print("=== Testing Login with PIN ===")
    
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "phone": "9876543210",
        "pin": "1234"
    })
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_login_wrong_pin():
    """Test login with wrong PIN"""
    print("=== Testing Login with Wrong PIN ===")
    
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "phone": "9876543210",
        "pin": "9999"
    })
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_login_invalid_phone():
    """Test login with invalid phone"""
    print("=== Testing Login with Invalid Phone ===")
    
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "phone": "123",
        "pin": "1234"
    })
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_login_nonexistent_user():
    """Test login with non-existent user"""
    print("=== Testing Login with Non-existent User ===")
    
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "phone": "9999999999",
        "pin": "1234"
    })
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_pin_rate_limiting():
    """Test PIN rate limiting (5 attempts, then lock)"""
    print("=== Testing PIN Rate Limiting ===")
    
    # Try 6 wrong PINs
    for i in range(6):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "phone": "9876543210",
            "pin": f"{i:04d}"  # 0000, 0001, 0002, etc.
        })
        
        print(f"Attempt {i+1}: Status {response.status_code}")
        if response.status_code == 200:
            print("  Unexpected success!")
        else:
            print(f"  Message: {response.json().get('message', 'No message')}")
    
    print()

def test_complete_flow():
    """Test complete authentication flow"""
    print("=== Testing Complete Flow ===")
    
    # Step 1: Check new phone
    print("Step 1: Check new phone")
    response = requests.post(f"{BASE_URL}/api/auth/check-phone", json={
        "phone": "5555555555"
    })
    print(f"  Response: {response.json()}")
    
    # Step 2: Setup account
    print("Step 2: Setup account")
    response = requests.post(f"{BASE_URL}/api/auth/setup-account", json={
        "phone": "5555555555",
        "shop_name": "Flow Test Store",
        "shop_address": "456 Flow Street",
        "pin": "5678",
        "confirm_pin": "5678"
    })
    print(f"  Response: {response.json()}")
    
    # Step 3: Login with PIN
    print("Step 3: Login with PIN")
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "phone": "5555555555",
        "pin": "5678"
    })
    print(f"  Response: {response.json()}")
    
    print()

if __name__ == "__main__":
    print("PIN Authentication System Test")
    print("=" * 50)
    print("Make sure the Flask app is running on localhost:5000")
    print()
    
    try:
        test_check_phone_new_user()
        test_setup_account()
        test_check_phone_existing_user()
        test_login_with_pin()
        test_login_wrong_pin()
        test_login_invalid_phone()
        test_login_nonexistent_user()
        test_pin_rate_limiting()
        test_complete_flow()
        
        print("All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Flask app.")
        print("Make sure the app is running with: python app.py")
    except Exception as e:
        print(f"Error: {e}")
