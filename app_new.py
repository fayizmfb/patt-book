"""
Patt Book - Email OTP Authentication API
Secure authentication with Email OTP and Phone as unique identifier
"""

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from datetime import datetime, timedelta
from database import init_db, get_db
from auth import (
    generate_otp, send_email_otp, store_otp, verify_otp,
    generate_jwt_token, verify_jwt_token, check_email_phone_exists,
    check_email_exists, check_phone_exists
)
import sqlite3
import os
import requests
import json

# Windsurf Compatibility Fixes
os.environ['DISABLE_UI_CUSTOMIZATION'] = '1'
os.environ['DISABLE_ICON_THEMES'] = '1'
os.environ['FORCE_DEFAULT_THEME'] = '1'
os.environ['DISABLE_FANCY_FEATURES'] = '1'
os.environ['DISABLE_FILE_WATCHING'] = '1'
os.environ['DISABLE_AUTO_RELOAD'] = '1'
os.environ['DISABLE_CUSTOM_FONTS'] = '1'
os.environ['FORCE_SIMPLE_RENDERING'] = '1'

app = Flask(__name__)
app.secret_key = 'patt-book-secret-key'

# Initialize database
try:
    init_db()
    print("Database initialized successfully")
except Exception as e:
    print(f"Database initialization error: {e}")

# ============================================================================ 
# AUTHENTICATION API ENDPOINTS
# ============================================================================

@app.route('/auth/signup', methods=['POST'])
def signup():
    """Signup endpoint - email + phone validation"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request data'}), 400
        
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        user_type = data.get('user_type', '').strip()
        shop_name = data.get('shop_name', '').strip() if user_type == 'retailer' else ''
        
        # Validation
        if not email or not phone or not user_type:
            return jsonify({'success': False, 'message': 'Email, phone, and user type are required'}), 400
        
        if user_type not in ['retailer', 'customer']:
            return jsonify({'success': False, 'message': 'Invalid user type'}), 400
        
        if user_type == 'retailer' and not shop_name:
            return jsonify({'success': False, 'message': 'Shop name is required for retailers'}), 400
        
        # Check if email already exists
        if check_email_exists(email):
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
        
        # Check if phone already exists
        if check_phone_exists(phone):
            return jsonify({'success': False, 'message': 'Phone number already registered'}), 400
        
        # Generate and send OTP
        otp = generate_otp()
        
        if not store_otp(email, otp):
            return jsonify({'success': False, 'message': 'Failed to generate OTP'}), 500
        
        if not send_email_otp(email, otp):
            return jsonify({'success': False, 'message': 'Failed to send OTP email'}), 500
        
        # Store signup data in session temporarily
        session['signup_data'] = {
            'email': email,
            'phone': phone,
            'user_type': user_type,
            'shop_name': shop_name
        }
        
        return jsonify({
            'success': True,
            'message': 'OTP sent to your email. Please verify to complete signup.',
            'email': email
        })
        
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/auth/verify-signup-otp', methods=['POST'])
def verify_signup_otp():
    """Verify signup OTP and create account"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request data'}), 400
        
        otp = data.get('otp', '').strip()
        
        if not otp:
            return jsonify({'success': False, 'message': 'OTP is required'}), 400
        
        # Get signup data from session
        signup_data = session.get('signup_data')
        if not signup_data:
            return jsonify({'success': False, 'message': 'Signup session expired. Please signup again.'}), 400
        
        email = signup_data['email']
        
        # Verify OTP
        result = verify_otp(email, otp)
        if not result['success']:
            return jsonify({'success': False, 'message': result['message']}), 400
        
        # Create account
        db = get_db()
        try:
            if signup_data['user_type'] == 'retailer':
                db.execute(
                    'INSERT INTO retailers (retailer_phone, shop_name, email, email_verified) VALUES (?, ?, ?, ?)',
                    (signup_data['phone'], signup_data['shop_name'], signup_data['email'], 1)
                )
            else:
                db.execute(
                    'INSERT INTO customers (phone, email, email_verified) VALUES (?, ?, ?)',
                    (signup_data['phone'], signup_data['email'], 1)
                )
            
            db.commit()
            
            # Clear signup session
            session.pop('signup_data', None)
            
            # Generate JWT token
            user_data = {
                'phone': signup_data['phone'],
                'email': signup_data['email'],
                'user_type': signup_data['user_type']
            }
            token = generate_jwt_token(user_data)
            
            return jsonify({
                'success': True,
                'message': 'Account created successfully!',
                'token': token,
                'user': {
                    'phone': signup_data['phone'],
                    'email': signup_data['email'],
                    'user_type': signup_data['user_type'],
                    'shop_name': signup_data.get('shop_name', '')
                }
            })
            
        except Exception as e:
            db.rollback()
            print(f"Account creation error: {e}")
            return jsonify({'success': False, 'message': 'Failed to create account'}), 500
        finally:
            db.close()
            
    except Exception as e:
        print(f"Verify signup OTP error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/auth/login', methods=['POST'])
def login():
    """Login endpoint - email + phone validation"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request data'}), 400
        
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        user_type = data.get('user_type', '').strip()
        
        # Validation
        if not email or not phone or not user_type:
            return jsonify({'success': False, 'message': 'Email, phone, and user type are required'}), 400
        
        if user_type not in ['retailer', 'customer']:
            return jsonify({'success': False, 'message': 'Invalid user type'}), 400
        
        # Check if email + phone combination exists
        if not check_email_phone_exists(email, phone, user_type):
            return jsonify({'success': False, 'message': 'Invalid email and phone combination'}), 400
        
        # Generate and send OTP
        otp = generate_otp()
        
        if not store_otp(email, otp):
            return jsonify({'success': False, 'message': 'Failed to generate OTP'}), 500
        
        if not send_email_otp(email, otp):
            return jsonify({'success': False, 'message': 'Failed to send OTP email'}), 500
        
        # Store login data in session temporarily
        session['login_data'] = {
            'email': email,
            'phone': phone,
            'user_type': user_type
        }
        
        return jsonify({
            'success': True,
            'message': 'OTP sent to your email. Please verify to login.',
            'email': email
        })
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/auth/verify-login-otp', methods=['POST'])
def verify_login_otp():
    """Verify login OTP and issue token"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request data'}), 400
        
        otp = data.get('otp', '').strip()
        
        if not otp:
            return jsonify({'success': False, 'message': 'OTP is required'}), 400
        
        # Get login data from session
        login_data = session.get('login_data')
        if not login_data:
            return jsonify({'success': False, 'message': 'Login session expired. Please login again.'}), 400
        
        email = login_data['email']
        
        # Verify OTP
        result = verify_otp(email, otp)
        if not result['success']:
            return jsonify({'success': False, 'message': result['message']}), 400
        
        # Get user details
        db = get_db()
        try:
            if login_data['user_type'] == 'retailer':
                user = db.execute(
                    'SELECT * FROM retailers WHERE email = ? AND retailer_phone = ?',
                    (login_data['email'], login_data['phone'])
                ).fetchone()
            else:
                user = db.execute(
                    'SELECT * FROM customers WHERE email = ? AND phone = ?',
                    (login_data['email'], login_data['phone'])
                ).fetchone()
            
            if not user:
                return jsonify({'success': False, 'message': 'User not found'}), 400
            
            # Clear login session
            session.pop('login_data', None)
            
            # Generate JWT token
            user_data = {
                'phone': login_data['phone'],
                'email': login_data['email'],
                'user_type': login_data['user_type']
            }
            token = generate_jwt_token(user_data)
            
            return jsonify({
                'success': True,
                'message': 'Login successful!',
                'token': token,
                'user': {
                    'phone': login_data['phone'],
                    'email': login_data['email'],
                    'user_type': login_data['user_type'],
                    'shop_name': user['shop_name'] if login_data['user_type'] == 'retailer' else ''
                }
            })
            
        except Exception as e:
            print(f"Login verification error: {e}")
            return jsonify({'success': False, 'message': 'Login failed'}), 500
        finally:
            db.close()
            
    except Exception as e:
        print(f"Verify login OTP error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

# ============================================================================ 
# WEB ROUTES (for backward compatibility)
# ============================================================================

@app.route('/')
def home():
    """Root route - redirect to role selection"""
    return redirect(url_for('role_selection'))

@app.route('/role-selection')
def role_selection():
    """Role selection screen - First page users see"""
    return render_template('role_selection.html')

@app.route('/retailer/login')
def retailer_login():
    """Retailer login page"""
    return render_template('retailer_login.html')

@app.route('/customer/login')
def customer_login():
    """Customer login page"""
    return render_template('customer_login.html')

@app.route('/retailer/register')
def retailer_register():
    """Retailer registration page"""
    return render_template('retailer_register.html')

@app.route('/customer/register')
def customer_register():
    """Customer registration page"""
    return render_template('customer_register.html')

@app.route('/retailer/dashboard')
def retailer_dashboard():
    """Retailer dashboard - JWT protected"""
    return render_template('retailer_dashboard.html')

@app.route('/customer/dashboard')
def customer_dashboard():
    """Customer dashboard - JWT protected"""
    return render_template('customer_dashboard.html')

@app.route('/health')
def health_check():
    """Health check for monitoring"""
    return {"status": "ok", "message": "Patt Book backend is running"}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
