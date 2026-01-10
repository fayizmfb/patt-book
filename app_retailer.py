"""
Patt Book - Retailer Only Application
WhatsApp OTP Authentication & Ledger Management
"""

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from datetime import datetime
import jwt
import os
from database_retailer import get_db, cleanup_expired_otps
from whatsapp_service import (
    generate_otp, send_whatsapp_otp, store_otp, verify_otp,
    send_credit_added_notification, send_payment_recorded_notification
)
import threading

# Flask Configuration
app = Flask(__name__)
app.secret_key = 'patt-book-retailer-secret'

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'patt-book-retailer-jwt-secret')
JWT_EXPIRY = 24  # hours

# Test Mode
TEST_MODE = os.environ.get('TEST_MODE', 'true').lower() == 'true'

# Initialize database
try:
    from database_retailer import init_db
    init_db()
    print("Retailer database initialized successfully")
except Exception as e:
    print(f"Database initialization error: {e}")

# Helper Functions
def generate_jwt_token(retailer_data):
    """Generate JWT token for retailer"""
    payload = {
        'retailer_id': retailer_data['id'],
        'phone': retailer_data['phone'],
        'shop_name': retailer_data['shop_name'],
        'exp': datetime.now().timestamp() + (JWT_EXPIRY * 3600)
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    return token

def verify_jwt_token(token):
    """Verify JWT token and return retailer data"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        retailer_data = verify_jwt_token(token)
        if not retailer_data:
            return jsonify({'success': False, 'message': 'Invalid or expired token'}), 401
        
        request.retailer_data = retailer_data
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """Retailer signup with WhatsApp OTP"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request data'}), 400
        
        phone = data.get('phone', '').strip()
        shop_name = data.get('shop_name', '').strip()
        shop_address = data.get('shop_address', '').strip()
        shop_photo_url = data.get('shop_photo_url', '').strip()
        
        # Validation
        if not phone or not shop_name or not shop_address:
            return jsonify({'success': False, 'message': 'Phone, shop name, and address are required'}), 400
        
        # Check if phone already exists
        db = get_db()
        try:
            existing = db.execute('SELECT id FROM retailers WHERE phone = ?', (phone,)).fetchone()
            if existing:
                return jsonify({'success': False, 'message': 'Phone number already registered'}), 400
            
            # Generate and send OTP
            otp = generate_otp()
            
            if not store_otp(phone, otp):
                return jsonify({'success': False, 'message': 'Failed to generate OTP'}), 500
            
            if not send_whatsapp_otp(phone, otp):
                return jsonify({'success': False, 'message': 'Failed to send OTP via WhatsApp'}), 500
            
            # Store signup data in session
            session['signup_data'] = {
                'phone': phone,
                'shop_name': shop_name,
                'shop_address': shop_address,
                'shop_photo_url': shop_photo_url
            }
            
            return jsonify({
                'success': True,
                'message': 'OTP sent via WhatsApp. Please verify to complete signup.',
                'phone': phone
            })
            
        except Exception as e:
            print(f"Signup error: {e}")
            return jsonify({'success': False, 'message': 'Signup failed'}), 500
        finally:
            db.close()
            
    except Exception as e:
        print(f"Signup endpoint error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/auth/verify-signup-otp', methods=['POST'])
def verify_signup_otp():
    """Verify signup OTP and create retailer account"""
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
        
        phone = signup_data['phone']
        
        # Verify OTP
        result = verify_otp(phone, otp)
        if not result['success']:
            return jsonify({'success': False, 'message': result['message']}), 400
        
        # Create retailer account
        db = get_db()
        try:
            cursor = db.execute(
                'INSERT INTO retailers (phone, shop_name, shop_address, shop_photo_url) VALUES (?, ?, ?, ?)',
                (signup_data['phone'], signup_data['shop_name'], signup_data['shop_address'], signup_data['shop_photo_url'])
            )
            retailer_id = cursor.lastrowid
            db.commit()
            
            # Clear signup session
            session.pop('signup_data', None)
            
            # Generate JWT token
            retailer_data = {
                'id': retailer_id,
                'phone': signup_data['phone'],
                'shop_name': signup_data['shop_name']
            }
            token = generate_jwt_token(retailer_data)
            
            return jsonify({
                'success': True,
                'message': 'Account created successfully!',
                'token': token,
                'retailer': retailer_data
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

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Retailer login with WhatsApp OTP"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request data'}), 400
        
        phone = data.get('phone', '').strip()
        
        if not phone:
            return jsonify({'success': False, 'message': 'Phone number is required'}), 400
        
        # Check if retailer exists
        db = get_db()
        try:
            retailer = db.execute('SELECT * FROM retailers WHERE phone = ?', (phone,)).fetchone()
            if not retailer:
                return jsonify({'success': False, 'message': 'Phone number not registered'}), 400
            
            # Generate and send OTP
            otp = generate_otp()
            
            if not store_otp(phone, otp):
                return jsonify({'success': False, 'message': 'Failed to generate OTP'}), 500
            
            if not send_whatsapp_otp(phone, otp):
                return jsonify({'success': False, 'message': 'Failed to send OTP via WhatsApp'}), 500
            
            # Store login data in session
            session['login_data'] = {'phone': phone}
            
            return jsonify({
                'success': True,
                'message': 'OTP sent via WhatsApp. Please verify to login.',
                'phone': phone
            })
            
        except Exception as e:
            print(f"Login error: {e}")
            return jsonify({'success': False, 'message': 'Login failed'}), 500
        finally:
            db.close()
            
    except Exception as e:
        print(f"Login endpoint error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/auth/verify-login-otp', methods=['POST'])
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
        
        phone = login_data['phone']
        
        # Verify OTP
        result = verify_otp(phone, otp)
        if not result['success']:
            return jsonify({'success': False, 'message': result['message']}), 400
        
        # Get retailer details
        db = get_db()
        try:
            retailer = db.execute('SELECT * FROM retailers WHERE phone = ?', (phone,)).fetchone()
            if not retailer:
                return jsonify({'success': False, 'message': 'Retailer not found'}), 400
            
            # Clear login session
            session.pop('login_data', None)
            
            # Generate JWT token
            retailer_data = {
                'id': retailer['id'],
                'phone': retailer['phone'],
                'shop_name': retailer['shop_name']
            }
            token = generate_jwt_token(retailer_data)
            
            return jsonify({
                'success': True,
                'message': 'Login successful!',
                'token': token,
                'retailer': retailer_data
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
# DEBTOR MANAGEMENT ROUTES
# ============================================================================

@app.route('/api/debtors', methods=['POST'])
@require_auth
def add_debtor():
    """Add new debtor or update existing"""
    try:
        data = request.get_json()
        retailer_id = request.retailer_data['retailer_id']
        
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        credit_amount = data.get('credit_amount', 0)
        description = data.get('description', '').strip()
        
        if not name or not phone:
            return jsonify({'success': False, 'message': 'Name and phone are required'}), 400
        
        if credit_amount <= 0:
            return jsonify({'success': False, 'message': 'Credit amount must be greater than 0'}), 400
        
        db = get_db()
        try:
            # Check if debtor already exists
            existing_debtor = db.execute(
                'SELECT id, total_due FROM debtors WHERE retailer_id = ? AND phone = ?',
                (retailer_id, phone)
            ).fetchone()
            
            if existing_debtor:
                # Update existing debtor
                debtor_id = existing_debtor['id']
                new_total_due = existing_debtor['total_due'] + credit_amount
                
                db.execute(
                    'UPDATE debtors SET total_due = ? WHERE id = ?',
                    (new_total_due, debtor_id)
                )
            else:
                # Create new debtor
                cursor = db.execute(
                    'INSERT INTO debtors (retailer_id, name, phone, total_due) VALUES (?, ?, ?, ?)',
                    (retailer_id, name, phone, credit_amount)
                )
                debtor_id = cursor.lastrowid
                new_total_due = credit_amount
            
            # Add credit transaction
            db.execute(
                'INSERT INTO transactions (debtor_id, type, amount, description) VALUES (?, ?, ?, ?)',
                (debtor_id, 'credit', credit_amount, description)
            )
            
            db.commit()
            
            # Send WhatsApp notification (async)
            shop_name = request.retailer_data['shop_name']
            notification_thread = threading.Thread(
                target=send_credit_added_notification,
                args=(name, shop_name, credit_amount, new_total_due, phone)
            )
            notification_thread.daemon = True
            notification_thread.start()
            
            return jsonify({
                'success': True,
                'message': 'Debtor added successfully',
                'debtor_id': debtor_id,
                'total_due': new_total_due
            })
            
        except Exception as e:
            db.rollback()
            print(f"Add debtor error: {e}")
            return jsonify({'success': False, 'message': 'Failed to add debtor'}), 500
        finally:
            db.close()
            
    except Exception as e:
        print(f"Add debtor endpoint error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/debtors', methods=['GET'])
@require_auth
def get_debtors():
    """Get debtors list with sorting"""
    try:
        retailer_id = request.retailer_data['retailer_id']
        sort_by = request.args.get('sort', 'name')
        order = request.args.get('order', 'asc')
        
        db = get_db()
        try:
            # Build query based on sort option
            if sort_by == 'amount' and order == 'asc':
                query = 'SELECT * FROM debtors WHERE retailer_id = ? ORDER BY total_due ASC'
            elif sort_by == 'amount' and order == 'desc':
                query = 'SELECT * FROM debtors WHERE retailer_id = ? ORDER BY total_due DESC'
            elif sort_by == 'name' and order == 'desc':
                query = 'SELECT * FROM debtors WHERE retailer_id = ? ORDER BY name DESC'
            elif sort_by == 'created_at' and order == 'asc':
                query = 'SELECT * FROM debtors WHERE retailer_id = ? ORDER BY created_at ASC'
            elif sort_by == 'created_at' and order == 'desc':
                query = 'SELECT * FROM debtors WHERE retailer_id = ? ORDER BY created_at DESC'
            else:  # default: name asc
                query = 'SELECT * FROM debtors WHERE retailer_id = ? ORDER BY name ASC'
            
            debtors = db.execute(query, (retailer_id,)).fetchall()
            
            return jsonify({
                'success': True,
                'debtors': [dict(debtor) for debtor in debtors]
            })
            
        except Exception as e:
            print(f"Get debtors error: {e}")
            return jsonify({'success': False, 'message': 'Failed to fetch debtors'}), 500
        finally:
            db.close()
            
    except Exception as e:
        print(f"Get debtors endpoint error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/payments', methods=['POST'])
@require_auth
def add_payment():
    """Add payment for debtor"""
    try:
        data = request.get_json()
        retailer_id = request.retailer_data['retailer_id']
        
        debtor_id = data.get('debtor_id')
        amount = data.get('amount', 0)
        
        if not debtor_id or amount <= 0:
            return jsonify({'success': False, 'message': 'Debtor ID and valid amount are required'}), 400
        
        db = get_db()
        try:
            # Get debtor details
            debtor = db.execute(
                'SELECT * FROM debtors WHERE id = ? AND retailer_id = ?',
                (debtor_id, retailer_id)
            ).fetchone()
            
            if not debtor:
                return jsonify({'success': False, 'message': 'Debtor not found'}), 404
            
            if amount > debtor['total_due']:
                return jsonify({'success': False, 'message': 'Payment amount exceeds total due'}), 400
            
            # Update total due
            new_balance = debtor['total_due'] - amount
            db.execute(
                'UPDATE debtors SET total_due = ? WHERE id = ?',
                (new_balance, debtor_id)
            )
            
            # Add payment transaction
            db.execute(
                'INSERT INTO transactions (debtor_id, type, amount) VALUES (?, ?, ?)',
                (debtor_id, 'payment', amount)
            )
            
            db.commit()
            
            # Send WhatsApp notification (async)
            shop_name = request.retailer_data['shop_name']
            notification_thread = threading.Thread(
                target=send_payment_recorded_notification,
                args=(debtor['name'], shop_name, amount, new_balance, debtor['phone'])
            )
            notification_thread.daemon = True
            notification_thread.start()
            
            return jsonify({
                'success': True,
                'message': 'Payment recorded successfully',
                'remaining_balance': new_balance
            })
            
        except Exception as e:
            db.rollback()
            print(f"Add payment error: {e}")
            return jsonify({'success': False, 'message': 'Failed to record payment'}), 500
        finally:
            db.close()
            
    except Exception as e:
        print(f"Add payment endpoint error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/settings', methods=['GET'])
@require_auth
def get_settings():
    """Get retailer settings"""
    try:
        retailer_id = request.retailer_data['retailer_id']
        
        db = get_db()
        try:
            retailer = db.execute(
                'SELECT * FROM retailers WHERE id = ?',
                (retailer_id,)
            ).fetchone()
            
            if not retailer:
                return jsonify({'success': False, 'message': 'Retailer not found'}), 404
            
            return jsonify({
                'success': True,
                'retailer': dict(retailer)
            })
            
        except Exception as e:
            print(f"Get settings error: {e}")
            return jsonify({'success': False, 'message': 'Failed to fetch settings'}), 500
        finally:
            db.close()
            
    except Exception as e:
        print(f"Get settings endpoint error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

# ============================================================================
# WEB ROUTES
# ============================================================================

@app.route('/')
def home():
    """Home page - redirect to auth"""
    return render_template('retailer_auth.html')

@app.route('/dashboard')
def dashboard():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/health')
def health_check():
    """Health check"""
    return {"status": "ok", "message": "Patt Book Retailer API is running"}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
