"""
Patt Book - Production Backend API
Role-based authentication for Retailer and Customer
"""

from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import jwt
import random
import string
import os

# Import database functions
from database_new import *

app = Flask(__name__)
app.secret_key = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')

# Initialize database
init_db()

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def generate_jwt_token(user_id, user_type):
    """Generate JWT token"""
    payload = {
        'user_id': user_id,
        'user_type': user_type,
        'exp': datetime.utcnow() + timedelta(days=30),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, app.secret_key, algorithm='HS256')

def verify_jwt_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@app.route('/api/auth/send-otp', methods=['POST'])
def send_otp():
    """Send OTP for login/signup"""
    try:
        data = request.get_json()
        mobile_number = data.get('mobile_number')
        
        if not mobile_number or len(mobile_number) != 10:
            return jsonify({'success': False, 'message': 'Valid 10-digit mobile number required'})
        
        # Generate OTP
        otp = generate_otp()
        
        # Store OTP in database
        create_otp_request(mobile_number, otp)
        
        # TODO: Send OTP via WhatsApp API
        # For now, return OTP for testing (remove in production)
        if os.environ.get('TEST_MODE', 'true').lower() == 'true':
            return jsonify({
                'success': True, 
                'message': 'OTP sent successfully',
                'otp': otp  # Remove in production
            })
        
        return jsonify({'success': True, 'message': 'OTP sent successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Failed to send OTP'})

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp_endpoint():
    """Verify OTP and login/signup"""
    try:
        data = request.get_json()
        mobile_number = data.get('mobile_number')
        otp = data.get('otp')
        user_type = data.get('user_type')  # 'retailer' or 'customer'
        
        if not all([mobile_number, otp, user_type]):
            return jsonify({'success': False, 'message': 'All fields required'})
        
        # Verify OTP
        if not verify_otp(mobile_number, otp):
            return jsonify({'success': False, 'message': 'Invalid or expired OTP'})
        
        # Check if user exists
        user = get_user_by_mobile(mobile_number)
        
        if user:
            # Existing user - login
            if user['user_type'] != user_type:
                return jsonify({'success': False, 'message': 'User type mismatch'})
            
            token = generate_jwt_token(user['id'], user['user_type'])
            create_session(user['id'], token)
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': dict(user),
                'token': token,
                'is_new_user': False
            })
        else:
            # New user - return user data for account creation
            return jsonify({
                'success': True,
                'message': 'OTP verified. Please complete account creation.',
                'is_new_user': True,
                'user_type': user_type
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'OTP verification failed'})

@app.route('/api/auth/create-account', methods=['POST'])
def create_account():
    """Create new account after OTP verification"""
    try:
        data = request.get_json()
        mobile_number = data.get('mobile_number')
        user_type = data.get('user_type')
        
        if not all([mobile_number, user_type]):
            return jsonify({'success': False, 'message': 'Mobile number and user type required'})
        
        # Check if user already exists
        existing_user = get_user_by_mobile(mobile_number)
        if existing_user:
            return jsonify({'success': False, 'message': 'User already exists'})
        
        if user_type == 'retailer':
            # Validate required retailer fields
            required_fields = ['shop_name', 'shop_address', 'shop_photo_url', 'latitude', 'longitude']
            if not all(data.get(field) for field in required_fields):
                return jsonify({'success': False, 'message': 'All retailer fields required'})
            
            user_id = create_user(
                mobile_number=mobile_number,
                user_type='retailer',
                shop_name=data['shop_name'],
                shop_address=data['shop_address'],
                shop_photo_url=data['shop_photo_url'],
                latitude=data['latitude'],
                longitude=data['longitude']
            )
            
        elif user_type == 'customer':
            # Validate required customer fields
            if not data.get('customer_name'):
                return jsonify({'success': False, 'message': 'Customer name required'})
            
            user_id = create_user(
                mobile_number=mobile_number,
                user_type='customer',
                customer_name=data['customer_name']
            )
        else:
            return jsonify({'success': False, 'message': 'Invalid user type'})
        
        # Get created user
        user = get_user_by_id(user_id)
        token = generate_jwt_token(user_id, user_type)
        create_session(user_id, token)
        
        return jsonify({
            'success': True,
            'message': 'Account created successfully',
            'user': dict(user),
            'token': token
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Account creation failed'})

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500

# ============================================================================
# RUN APP
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)