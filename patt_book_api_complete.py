"""
PATT BOOK COMPLETE API - Single File Version
Role-based authentication for Retailer and Customer
"""

import sqlite3
import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import jwt
import random
import string

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DATABASE_PATH = 'patt_book.db'

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize database with Patt Book schema"""
    db = get_db()
    
    # Drop all existing tables for clean start
    db.execute('DROP TABLE IF EXISTS users')
    db.execute('DROP TABLE IF EXISTS customers')
    db.execute('DROP TABLE IF EXISTS transactions')
    db.execute('DROP TABLE IF EXISTS otp_requests')
    db.execute('DROP TABLE IF EXISTS sessions')
    db.execute('DROP TABLE IF EXISTS reminders')
    
    # Create users table (for both retailer and customer)
    db.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mobile_number TEXT UNIQUE NOT NULL,
            user_type TEXT NOT NULL CHECK (user_type IN ('retailer', 'customer')),
            retailer_shop_name TEXT,
            retailer_shop_address TEXT,
            retailer_shop_photo_url TEXT,
            retailer_latitude REAL,
            retailer_longitude REAL,
            customer_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create customers table (retailer's customer list)
    db.execute('''
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            retailer_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            mobile_number TEXT NOT NULL,
            due_amount REAL DEFAULT 0.0,
            total_credit REAL DEFAULT 0.0,
            total_paid REAL DEFAULT 0.0,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (retailer_id) REFERENCES users (id),
            UNIQUE(retailer_id, mobile_number)
        )
    ''')
    
    # Create transactions table
    db.execute('''
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            retailer_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('credit', 'payment')),
            amount REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (retailer_id) REFERENCES users (id)
        )
    ''')
    
    # Create OTP requests table
    db.execute('''
        CREATE TABLE otp_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mobile_number TEXT NOT NULL,
            otp TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            is_used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create sessions table
    db.execute('''
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            device_id TEXT,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create reminders table (Sunday reminders)
    db.execute('''
        CREATE TABLE reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            retailer_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message TEXT,
            status TEXT DEFAULT 'sent',
            FOREIGN KEY (retailer_id) REFERENCES users (id),
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')
    
    # Create indexes
    db.execute('CREATE INDEX idx_users_mobile ON users(mobile_number)')
    db.execute('CREATE INDEX idx_users_type ON users(user_type)')
    db.execute('CREATE INDEX idx_customers_retailer ON customers(retailer_id)')
    db.execute('CREATE INDEX idx_customers_mobile ON customers(mobile_number)')
    db.execute('CREATE INDEX idx_transactions_customer ON transactions(customer_id)')
    db.execute('CREATE INDEX idx_transactions_retailer ON transactions(retailer_id)')
    db.execute('CREATE INDEX idx_sessions_token ON sessions(token)')
    db.execute('CREATE INDEX idx_sessions_user ON sessions(user_id)')
    db.execute('CREATE INDEX idx_otp_mobile ON otp_requests(mobile_number)')
    
    db.commit()
    db.close()

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def create_user(mobile_number, user_type, **kwargs):
    """Create a new user (retailer or customer)"""
    db = get_db()
    cursor = db.cursor()
    
    if user_type == 'retailer':
        cursor.execute('''
            INSERT INTO users (mobile_number, user_type, retailer_shop_name, 
                             retailer_shop_address, retailer_shop_photo_url,
                             retailer_latitude, retailer_longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (mobile_number, user_type, 
              kwargs.get('shop_name'),
              kwargs.get('shop_address'), 
              kwargs.get('shop_photo_url'),
              kwargs.get('latitude'),
              kwargs.get('longitude')))
    elif user_type == 'customer':
        cursor.execute('''
            INSERT INTO users (mobile_number, user_type, customer_name)
            VALUES (?, ?, ?)
        ''', (mobile_number, user_type, kwargs.get('customer_name')))
    
    user_id = cursor.lastrowid
    db.commit()
    db.close()
    return user_id

def get_user_by_mobile(mobile_number):
    """Get user by mobile number"""
    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE mobile_number = ?',
        (mobile_number,)
    ).fetchone()
    db.close()
    return user

def get_user_by_id(user_id):
    """Get user by ID"""
    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()
    db.close()
    return user

def create_session(user_id, token, device_id=None, expires_days=30):
    """Create a new session"""
    db = get_db()
    cursor = db.cursor()
    
    expires_at = datetime.utcnow() + timedelta(days=expires_days)
    
    cursor.execute('''
        INSERT INTO sessions (user_id, token, device_id, expires_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, token, device_id, expires_at))
    
    session_id = cursor.lastrowid
    db.commit()
    db.close()
    return session_id

def create_otp_request(mobile_number, otp, expires_minutes=10):
    """Create OTP request"""
    db = get_db()
    cursor = db.cursor()
    
    expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
    
    cursor.execute('''
        INSERT INTO otp_requests (mobile_number, otp, expires_at)
        VALUES (?, ?, ?)
    ''', (mobile_number, otp, expires_at))
    
    otp_id = cursor.lastrowid
    db.commit()
    db.close()
    return otp_id

def verify_otp(mobile_number, otp):
    """Verify OTP"""
    db = get_db()
    
    otp_request = db.execute('''
        SELECT * FROM otp_requests 
           WHERE mobile_number = ? AND otp = ? 
           AND expires_at > CURRENT_TIMESTAMP AND is_used = FALSE
           ORDER BY created_at DESC LIMIT 1
    ''', (mobile_number, otp)).fetchone()
    
    if otp_request:
        # Mark OTP as used
        db.execute(
            'UPDATE otp_requests SET is_used = TRUE WHERE id = ?',
            (otp_request['id'],)
        )
        db.commit()
    
    db.close()
    return otp_request is not None

# ============================================================================
# FLASK APPLICATION
# ============================================================================

app = Flask(__name__)
app.secret_key = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')

# Initialize database
init_db()

# ============================================================================
# AUTHENTICATION FUNCTIONS
# ============================================================================

def generate_otp():
    """Generate 6-digit OTP - Temporary hardcoded for testing"""
    return "242324"

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

# ============================================================================
# API ENDPOINTS
# ============================================================================

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
# RUN APPLICATION
# ============================================================================

if __name__ == '__main__':
    print("🚀 Starting Patt Book API Server...")
    print("📱 Default OTP: 242324")
    print("🔗 API Endpoints:")
    print("   POST /api/auth/send-otp")
    print("   POST /api/auth/verify-otp")
    print("   POST /api/auth/create-account")
    print("🌐 Server running on: http://localhost:5000")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
