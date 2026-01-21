"""
PIN Authentication Routes for Patt Book v1
Secure phone + PIN authentication without OTP dependency
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import uuid
import jwt
import os

from database import (
    create_retailer_with_pin,
    get_retailer_by_phone,
    update_retailer_pin,
    create_retailer_session,
    log_audit_action
)
from services.pin_auth import (
    hash_pin, verify_pin,
    is_pin_locked, record_pin_attempt,
    validate_phone_number, validate_pin,
    get_pin_attempts_remaining, get_lock_time_remaining
)

pin_auth_bp = Blueprint('pin_auth', __name__, url_prefix='/api/auth')

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

@pin_auth_bp.route('/check-phone', methods=['POST'])
def check_phone():
    """Check if phone number exists and determine next step"""
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        
        # Validate phone number
        valid, phone = validate_phone_number(phone)
        if not valid:
            return jsonify({
                'success': False,
                'message': phone  # Returns error message
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
        
        # Check if retailer exists
        retailer = get_retailer_by_phone(phone)
        
        if retailer:
            # Existing user - ask for PIN
            return jsonify({
                'success': True,
                'message': 'Phone number found. Please enter your PIN.',
                'user_exists': True,
                'requires_pin': True,
                'attempts_remaining': get_pin_attempts_remaining(phone)
            })
        else:
            # New user - ask to set up account
            return jsonify({
                'success': True,
                'message': 'New phone number. Please create your account.',
                'user_exists': False,
                'requires_setup': True
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred. Please try again.'
        }), 500

@pin_auth_bp.route('/setup-account', methods=['POST'])
def setup_account():
    """Set up new account with PIN"""
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        shop_name = data.get('shop_name', '').strip()
        shop_address = data.get('shop_address', '').strip()
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
                'message': 'PIN confirmation does not match'
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
                'message': 'Phone number already exists'
            }), 400
        
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
                'shop_address': shop_address
            },
            'token': token,
            'device_id': device_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred during setup'
        }), 500

@pin_auth_bp.route('/login', methods=['POST'])
def login_with_pin():
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

@pin_auth_bp.route('/change-pin', methods=['POST'])
def change_pin():
    """Change existing PIN"""
    try:
        # This would require authentication middleware
        # For now, returning placeholder
        return jsonify({
            'success': False,
            'message': 'Feature not implemented yet'
        }), 501
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred'
        }), 500
