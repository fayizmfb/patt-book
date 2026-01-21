"""
Authentication Routes for Patt Book v1
Phone Number + PIN authentication only (no OTP)
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from datetime import datetime, timedelta
import uuid
import jwt
import os

from database import (
    create_retailer_with_pin,
    get_retailer_by_phone,
    create_retailer_session,
    log_audit_action
)
from services.pin_auth import (
    hash_pin, verify_pin,
    is_pin_locked, record_pin_attempt,
    validate_phone_number, validate_pin,
    get_pin_attempts_remaining, get_lock_time_remaining
)

auth_bp = Blueprint('auth', __name__)

def generate_jwt_token(retailer_id):
    """Generate JWT token for authentication"""
    return jwt.encode(
        {
            'retailer_id': retailer_id,
            'exp': datetime.utcnow() + timedelta(days=7)
        },
        os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production'),
        algorithm='HS256'
    )

@auth_bp.route('/retailer-auth', methods=['GET', 'POST'])
def retailer_auth():
    """Main authentication page - handles both signup and login"""
    if request.method == 'GET':
        return render_template('auth.html')
    
    # Handle POST requests via API endpoints
    return jsonify({'success': False, 'message': 'Use API endpoints for authentication'})

@auth_bp.route('/api/signup', methods=['POST'])
def api_signup():
    """Retailer signup with PIN"""
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        shop_name = data.get('shop_name', '').strip()
        shop_address = data.get('shop_address', '').strip()
        shop_photo_url = data.get('shop_photo_url', '').strip()
        pin = data.get('pin', '').strip()
        confirm_pin = data.get('confirm_pin', '').strip()
        device_id = data.get('device_id', '').strip()
        
        # Validate phone number
        valid, phone = validate_phone_number(phone)
        if not valid:
            return jsonify({
                'success': False,
                'message': phone
            }), 400
        
        # Validate shop details
        if not shop_name or len(shop_name) < 2:
            return jsonify({
                'success': False,
                'message': 'Shop name must be at least 2 characters'
            }), 400
        
        if not shop_address or len(shop_address) < 5:
            return jsonify({
                'success': False,
                'message': 'Shop address must be at least 5 characters'
            }), 400
        
        # Validate PIN
        valid, pin = validate_pin(pin)
        if not valid:
            return jsonify({
                'success': False,
                'message': pin
            }), 400
        
        # Confirm PIN matches
        if pin != confirm_pin:
            return jsonify({
                'success': False,
                'message': 'PINs do not match'
            }), 400
        
        # Check if phone already exists
        existing = get_retailer_by_phone(phone)
        if existing:
            return jsonify({
                'success': False,
                'message': 'Phone number already registered'
            }), 400
        
        # Generate device ID if not provided
        if not device_id:
            device_id = str(uuid.uuid4())
        
        # Hash PIN
        pin_hash = hash_pin(pin)
        
        # Create retailer
        retailer_id = create_retailer_with_pin(phone, shop_name, shop_address, pin_hash)
        if not retailer_id:
            return jsonify({
                'success': False,
                'message': 'Failed to create account'
            }), 500
        
        # Generate JWT token
        token = generate_jwt_token(retailer_id)
        
        # Create session
        if not create_retailer_session(retailer_id, device_id, token):
            return jsonify({
                'success': False,
                'message': 'Failed to create session'
            }), 500
        
        # Log audit action
        log_audit_action(
            retailer_id=retailer_id,
            user_id=phone,
            action='ACCOUNT_CREATED',
            details=f'Device: {device_id}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Account created successfully!',
            'retailer': {
                'id': retailer_id,
                'phone': phone,
                'shop_name': shop_name,
                'shop_address': shop_address,
                'shop_photo_url': shop_photo_url
            },
            'token': token,
            'device_id': device_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred during signup'
        }), 500

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """Login with phone number and PIN"""
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        pin = data.get('pin', '').strip()
        device_id = data.get('device_id', '').strip()
        
        # Validate phone number
        valid, phone = validate_phone_number(phone)
        if not valid:
            return jsonify({
                'success': False,
                'message': phone
            }), 400
        
        # Validate PIN
        valid, pin = validate_pin(pin)
        if not valid:
            return jsonify({
                'success': False,
                'message': pin
            }), 400
        
        # Check if phone is locked
        locked, lock_until = is_pin_locked(phone)
        if locked:
            remaining_minutes = get_lock_time_remaining(phone)
            return jsonify({
                'success': False,
                'message': f'Account locked due to too many failed attempts. Try again in {remaining_minutes} minutes.',
                'locked': True,
                'lock_time_remaining': remaining_minutes
            }), 429
        
        # Get retailer
        retailer = get_retailer_by_phone(phone)
        if not retailer:
            record_pin_attempt(phone, False)
            return jsonify({
                'success': False,
                'message': 'User not found',
                'attempts_remaining': get_pin_attempts_remaining(phone)
            }), 404
        
        # Check if retailer has PIN set
        if not retailer['pin_hash']:
            return jsonify({
                'success': False,
                'message': 'Account not set up. Please create your account first.'
            }), 400
        
        # Verify PIN
        if not verify_pin(retailer['pin_hash'], pin):
            record_pin_attempt(phone, False)
            return jsonify({
                'success': False,
                'message': 'Invalid PIN',
                'attempts_remaining': get_pin_attempts_remaining(phone)
            }), 401
        
        # Successful login - record attempt
        record_pin_attempt(phone, True)
        
        # Generate device ID if not provided
        if not device_id:
            device_id = str(uuid.uuid4())
        
        # Generate JWT token
        token = generate_jwt_token(retailer['id'])
        
        # Create session
        if not create_retailer_session(retailer['id'], device_id, token):
            return jsonify({
                'success': False,
                'message': 'Failed to create session'
            }), 500
        
        # Log audit action
        log_audit_action(
            retailer_id=retailer['id'],
            user_id=phone,
            action='PIN_LOGIN',
            details=f'Device: {device_id}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Login successful!',
            'retailer': {
                'id': retailer['id'],
                'phone': retailer['phone'],
                'shop_name': retailer['shop_name'],
                'shop_address': retailer['shop_address'],
                'shop_photo_url': retailer['shop_photo_url']
            },
            'token': token,
            'device_id': device_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred during login'
        }), 500

@auth_bp.route('/logout')
def logout():
    """Logout user and clear session"""
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('auth.retailer_auth'))
