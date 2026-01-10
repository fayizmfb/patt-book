"""
Patt Book - Retailer-Only Ledger System
WhatsApp OTP Authentication + Automatic Customer Notifications
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, jsonify
from datetime import datetime, timedelta
from database import init_db, get_db
import sqlite3
import os
import requests
import json
import hashlib
import jwt
from functools import wraps

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
app.secret_key = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')

# Initialize retailer-only database
init_db()

# WhatsApp Configuration
WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
WHATSAPP_ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')
TEST_MODE = os.environ.get('TEST_MODE', 'true').lower() == 'true'

# ============================================================================ 
# AUTHENTICATION HELPERS
# ============================================================================

def is_retailer_logged_in():
    """Check if retailer is logged in"""
    return 'retailer_id' in session

def retailer_required(f):
    """Decorator to require retailer authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_retailer_logged_in():
            return redirect(url_for('retailer_auth'))
        return f(*args, **kwargs)
    return decorated_function

def generate_jwt_token(retailer_id):
    """Generate JWT token for retailer"""
    payload = {
        'retailer_id': retailer_id,
        'exp': datetime.utcnow() + timedelta(days=30),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, app.secret_key, algorithm='HS256')

def verify_jwt_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
        return payload['retailer_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# ============================================================================ 
# WHATSAPP OTP HELPERS
# ============================================================================

def generate_otp():
    """Generate 6-digit OTP"""
    import random
    return str(random.randint(100000, 999999))

def hash_otp(otp):
    """Hash OTP for storage"""
    return hashlib.sha256(otp.encode()).hexdigest()

def send_whatsapp_otp(phone_number, otp):
    """Send OTP via WhatsApp Cloud API"""
    if TEST_MODE:
        print(f"TEST MODE - WhatsApp OTP would be sent to {phone_number}: {otp}")
        return True
    
    try:
        url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {
            'Authorization': f'Bearer {WHATSAPP_ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": "LOGIN_OTP",
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": otp}
                        ]
                    }
                ]
            }
        }
        
        response = requests.post(url, json=data, headers=headers)
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error sending WhatsApp OTP: {e}")
        return False

def send_credit_added_notification(debtor_phone, debtor_name, shop_name, amount, total_due):
    """Send credit added notification to debtor"""
    if TEST_MODE:
        print(f"TEST MODE - WhatsApp notification would be sent to {debtor_phone}")
        print(f"Template: CREDIT_ADDED")
        print(f"Parameters: [{debtor_name}, {shop_name}, {amount}, {total_due}]")
        return True
    
    try:
        url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {
            'Authorization': f'Bearer {WHATSAPP_ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": debtor_phone,
            "type": "template",
            "template": {
                "name": "CREDIT_ADDED",
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": debtor_name},
                            {"type": "text", "text": shop_name},
                            {"type": "text", "text": str(amount)},
                            {"type": "text", "text": str(total_due)}
                        ]
                    }
                ]
            }
        }
        
        response = requests.post(url, json=data, headers=headers)
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error sending credit notification: {e}")
        return False

def send_payment_recorded_notification(debtor_phone, debtor_name, amount, shop_name, balance):
    """Send payment recorded notification to debtor"""
    if TEST_MODE:
        print(f"TEST MODE - WhatsApp notification would be sent to {debtor_phone}")
        print(f"Template: PAYMENT_RECORDED")
        print(f"Parameters: [{debtor_name}, {amount}, {shop_name}, {balance}]")
        return True
    
    try:
        url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {
            'Authorization': f'Bearer {WHATSAPP_ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": debtor_phone,
            "type": "template",
            "template": {
                "name": "PAYMENT_RECORDED",
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": debtor_name},
                            {"type": "text", "text": str(amount)},
                            {"type": "text", "text": shop_name},
                            {"type": "text", "text": str(balance)}
                        ]
                    }
                ]
            }
        }
        
        response = requests.post(url, json=data, headers=headers)
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error sending payment notification: {e}")
        return False

# ============================================================================ 
# MAIN ROUTES
# ============================================================================

@app.route('/')
def index():
    """Homepage - Retailer-only portal"""
    return render_template('role_selection.html')

@app.route('/retailer-auth')
def retailer_auth():
    """Retailer authentication page"""
    return render_template('retailer_auth.html')

@app.route('/dashboard')
@retailer_required
def dashboard():
    """Retailer dashboard"""
    retailer_id = session.get('retailer_id')
    db = get_db()
    
    try:
        # Get retailer info
        retailer = db.execute(
            'SELECT * FROM retailers WHERE id = ?',
            (retailer_id,)
        ).fetchone()
        
        # Get debtors count and total outstanding
        debtors_count = db.execute(
            'SELECT COUNT(*) as count FROM debtors WHERE retailer_id = ?',
            (retailer_id,)
        ).fetchone()['count']
        
        total_outstanding = db.execute(
            'SELECT SUM(total_due) as total FROM debtors WHERE retailer_id = ?',
            (retailer_id,)
        ).fetchone()['total'] or 0
        
        return render_template('dashboard_new.html', 
                           retailer=retailer,
                           debtors_count=debtors_count,
                           total_outstanding=total_outstanding)
        
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('retailer_auth'))
    finally:
        db.close()

# ============================================================================ 
# API ENDPOINTS
# ============================================================================

@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    """Retailer signup API"""
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        shop_name = data.get('shop_name', '').strip()
        shop_address = data.get('shop_address', '').strip()
        shop_photo_url = data.get('shop_photo_url', '').strip()
        
        # Validation
        if not phone or len(phone) != 10:
            return jsonify({'success': False, 'message': 'Valid 10-digit phone number required'})
        
        if not shop_name:
            return jsonify({'success': False, 'message': 'Shop name is required'})
        
        if not shop_address:
            return jsonify({'success': False, 'message': 'Shop address is required'})
        
        db = get_db()
        
        # Check if retailer already exists
        existing = db.execute(
            'SELECT id FROM retailers WHERE phone = ?',
            (phone,)
        ).fetchone()
        
        if existing:
            return jsonify({'success': False, 'message': 'Retailer with this phone number already exists'})
        
        # Generate and send OTP
        otp = generate_otp()
        otp_hash = hash_otp(otp)
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        # Store OTP request
        db.execute(
            'INSERT INTO otp_requests (phone, otp_hash, expires_at) VALUES (?, ?, ?)',
            (phone, otp_hash, expires_at)
        )
        db.commit()
        
        # Send WhatsApp OTP
        if send_whatsapp_otp(phone, otp):
            return jsonify({
                'success': True,
                'message': 'OTP sent via WhatsApp. Please verify to complete signup.',
                'phone': phone
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to send OTP. Please try again.'})
        
    except Exception as e:
        print(f"Error in signup: {e}")
        return jsonify({'success': False, 'message': 'An error occurred during signup'})
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/auth/verify-signup-otp', methods=['POST'])
def api_verify_signup_otp():
    """Verify signup OTP and create retailer account"""
    try:
        data = request.get_json()
        otp = data.get('otp', '').strip()
        
        if not otp or len(otp) != 6:
            return jsonify({'success': False, 'message': 'Valid 6-digit OTP required'})
        
        db = get_db()
        
        # Get latest OTP request
        otp_request = db.execute(
            'SELECT * FROM otp_requests ORDER BY created_at DESC LIMIT 1'
        ).fetchone()
        
        if not otp_request:
            return jsonify({'success': False, 'message': 'No OTP request found'})
        
        # Verify OTP
        if otp_request['attempts'] >= 3:
            return jsonify({'success': False, 'message': 'Maximum OTP attempts exceeded'})
        
        if datetime.utcnow() > datetime.fromisoformat(otp_request['expires_at']):
            return jsonify({'success': False, 'message': 'OTP has expired'})
        
        if hash_otp(otp) != otp_request['otp_hash']:
            # Increment attempts
            db.execute(
                'UPDATE otp_requests SET attempts = attempts + 1 WHERE id = ?',
                (otp_request['id'],)
            )
            db.commit()
            return jsonify({'success': False, 'message': 'Invalid OTP'})
        
        # OTP is valid - create retailer account
        # Note: In production, you'd store the signup data in session or temp table
        # For now, we'll use the phone from OTP request
        phone = otp_request['phone']
        shop_name = "Test Shop"  # This should come from session/temp storage
        shop_address = "Test Address"  # This should come from session/temp storage
        
        db.execute(
            'INSERT INTO retailers (phone, shop_name, shop_address) VALUES (?, ?, ?)',
            (phone, shop_name, shop_address)
        )
        db.commit()
        
        # Get retailer ID
        retailer = db.execute(
            'SELECT id FROM retailers WHERE phone = ?',
            (phone,)
        ).fetchone()
        
        # Generate JWT token
        token = generate_jwt_token(retailer['id'])
        
        # Clean up OTP requests
        db.execute('DELETE FROM otp_requests WHERE phone = ?', (phone,))
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Account created successfully!',
            'token': token,
            'retailer': {
                'id': retailer['id'],
                'phone': phone,
                'shop_name': shop_name,
                'shop_address': shop_address
            }
        })
        
    except Exception as e:
        print(f"Error verifying signup OTP: {e}")
        return jsonify({'success': False, 'message': 'An error occurred during verification'})
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Retailer login API"""
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        
        if not phone or len(phone) != 10:
            return jsonify({'success': False, 'message': 'Valid 10-digit phone number required'})
        
        db = get_db()
        
        # Check if retailer exists
        retailer = db.execute(
            'SELECT id FROM retailers WHERE phone = ?',
            (phone,)
        ).fetchone()
        
        if not retailer:
            return jsonify({'success': False, 'message': 'Retailer not found'})
        
        # Generate and send OTP
        otp = generate_otp()
        otp_hash = hash_otp(otp)
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        # Store OTP request
        db.execute(
            'INSERT INTO otp_requests (phone, otp_hash, expires_at) VALUES (?, ?, ?)',
            (phone, otp_hash, expires_at)
        )
        db.commit()
        
        # Send WhatsApp OTP
        if send_whatsapp_otp(phone, otp):
            return jsonify({
                'success': True,
                'message': 'OTP sent via WhatsApp. Please verify to login.',
                'phone': phone
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to send OTP. Please try again.'})
        
    except Exception as e:
        print(f"Error in login: {e}")
        return jsonify({'success': False, 'message': 'An error occurred during login'})
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/auth/verify-login-otp', methods=['POST'])
def api_verify_login_otp():
    """Verify login OTP"""
    try:
        data = request.get_json()
        otp = data.get('otp', '').strip()
        
        if not otp or len(otp) != 6:
            return jsonify({'success': False, 'message': 'Valid 6-digit OTP required'})
        
        db = get_db()
        
        # Get latest OTP request
        otp_request = db.execute(
            'SELECT * FROM otp_requests ORDER BY created_at DESC LIMIT 1'
        ).fetchone()
        
        if not otp_request:
            return jsonify({'success': False, 'message': 'No OTP request found'})
        
        # Verify OTP
        if otp_request['attempts'] >= 3:
            return jsonify({'success': False, 'message': 'Maximum OTP attempts exceeded'})
        
        if datetime.utcnow() > datetime.fromisoformat(otp_request['expires_at']):
            return jsonify({'success': False, 'message': 'OTP has expired'})
        
        if hash_otp(otp) != otp_request['otp_hash']:
            # Increment attempts
            db.execute(
                'UPDATE otp_requests SET attempts = attempts + 1 WHERE id = ?',
                (otp_request['id'],)
            )
            db.commit()
            return jsonify({'success': False, 'message': 'Invalid OTP'})
        
        # OTP is valid - get retailer info
        retailer = db.execute(
            'SELECT * FROM retailers WHERE phone = ?',
            (otp_request['phone'],)
        ).fetchone()
        
        if not retailer:
            return jsonify({'success': False, 'message': 'Retailer not found'})
        
        # Generate JWT token
        token = generate_jwt_token(retailer['id'])
        
        # Clean up OTP requests
        db.execute('DELETE FROM otp_requests WHERE phone = ?', (otp_request['phone'],))
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Login successful!',
            'token': token,
            'retailer': {
                'id': retailer['id'],
                'phone': retailer['phone'],
                'shop_name': retailer['shop_name'],
                'shop_address': retailer['shop_address'],
                'shop_photo_url': retailer['shop_photo_url']
            }
        })
        
    except Exception as e:
        print(f"Error verifying login OTP: {e}")
        return jsonify({'success': False, 'message': 'An error occurred during verification'})
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/debtors', methods=['POST'])
def api_add_debtor():
    """Add debtor API"""
    try:
        # Verify JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'message': 'Authentication required'})
        
        token = auth_header.split(' ')[1]
        retailer_id = verify_jwt_token(token)
        if not retailer_id:
            return jsonify({'success': False, 'message': 'Invalid or expired token'})
        
        data = request.get_json()
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        credit_amount = float(data.get('credit_amount', 0))
        description = data.get('description', '').strip()
        
        # Validation
        if not name or not phone or credit_amount <= 0:
            return jsonify({'success': False, 'message': 'Name, phone, and credit amount are required'})
        
        if len(phone) != 10:
            return jsonify({'success': False, 'message': 'Valid 10-digit phone number required'})
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if debtor exists for this retailer
        existing_debtor = cursor.execute(
            'SELECT id, total_due FROM debtors WHERE retailer_id = ? AND phone = ?',
            (retailer_id, phone)
        ).fetchone()
        
        if existing_debtor:
            # Update existing debtor
            new_total = existing_debtor['total_due'] + credit_amount
            cursor.execute(
                'UPDATE debtors SET total_due = ? WHERE id = ?',
                (new_total, existing_debtor['id'])
            )
            debtor_id = existing_debtor['id']
        else:
            # Create new debtor
            cursor.execute(
                'INSERT INTO debtors (retailer_id, name, phone, total_due) VALUES (?, ?, ?, ?)',
                (retailer_id, name, phone, credit_amount)
            )
            debtor_id = cursor.lastrowid
            new_total = credit_amount
        
        # Add transaction record
        cursor.execute(
            'INSERT INTO transactions (debtor_id, type, amount, description) VALUES (?, ?, ?, ?)',
            (debtor_id, 'credit', credit_amount, description)
        )
        
        db.commit()
        
        # Get retailer info for WhatsApp notification
        retailer = db.execute(
            'SELECT shop_name FROM retailers WHERE id = ?',
            (retailer_id,)
        ).fetchone()
        
        # Send WhatsApp notification (async)
        send_credit_added_notification(phone, name, retailer['shop_name'], credit_amount, new_total)
        
        return jsonify({
            'success': True,
            'message': 'Debtor added successfully!',
            'debtor_id': debtor_id,
            'total_due': new_total
        })
        
    except Exception as e:
        print(f"Error adding debtor: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'})
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/debtors', methods=['GET'])
def api_get_debtors():
    """Get debtors list API"""
    try:
        # Verify JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'message': 'Authentication required'})
        
        token = auth_header.split(' ')[1]
        retailer_id = verify_jwt_token(token)
        if not retailer_id:
            return jsonify({'success': False, 'message': 'Invalid or expired token'})
        
        # Get sorting parameters
        sort_field = request.args.get('sort', 'name')
        sort_order = request.args.get('order', 'asc')
        
        # Validate sort field
        valid_sort_fields = ['name', 'total_due', 'created_at']
        if sort_field not in valid_sort_fields:
            sort_field = 'name'
        
        # Validate sort order
        if sort_order not in ['asc', 'desc']:
            sort_order = 'asc'
        
        db = get_db()
        
        # Get debtors with sorting
        query = f'SELECT * FROM debtors WHERE retailer_id = ? ORDER BY {sort_field} {sort_order}'
        debtors = db.execute(query, (retailer_id,)).fetchall()
        
        return jsonify({
            'success': True,
            'debtors': [dict(debtor) for debtor in debtors]
        })
        
    except Exception as e:
        print(f"Error getting debtors: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'})
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/payments', methods=['POST'])
def api_add_payment():
    """Add payment API"""
    try:
        # Verify JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'message': 'Authentication required'})
        
        token = auth_header.split(' ')[1]
        retailer_id = verify_jwt_token(token)
        if not retailer_id:
            return jsonify({'success': False, 'message': 'Invalid or expired token'})
        
        data = request.get_json()
        debtor_id = data.get('debtor_id')
        amount = float(data.get('amount', 0))
        
        # Validation
        if not debtor_id or amount <= 0:
            return jsonify({'success': False, 'message': 'Debtor ID and payment amount are required'})
        
        db = get_db()
        
        # Get debtor info
        debtor = db.execute(
            'SELECT * FROM debtors WHERE id = ? AND retailer_id = ?',
            (debtor_id, retailer_id)
        ).fetchone()
        
        if not debtor:
            return jsonify({'success': False, 'message': 'Debtor not found'})
        
        if amount > debtor['total_due']:
            return jsonify({'success': False, 'message': 'Payment amount exceeds outstanding balance'})
        
        # Update debtor balance
        new_balance = debtor['total_due'] - amount
        db.execute(
            'UPDATE debtors SET total_due = ? WHERE id = ?',
            (new_balance, debtor_id)
        )
        
        # Add transaction record
        db.execute(
            'INSERT INTO transactions (debtor_id, type, amount, description) VALUES (?, ?, ?, ?)',
            (debtor_id, 'payment', amount, 'Payment received')
        )
        
        db.commit()
        
        # Get retailer info for WhatsApp notification
        retailer = db.execute(
            'SELECT shop_name FROM retailers WHERE id = ?',
            (retailer_id,)
        ).fetchone()
        
        # Send WhatsApp notification (async)
        send_payment_recorded_notification(debtor['phone'], debtor['name'], amount, retailer['shop_name'], new_balance)
        
        return jsonify({
            'success': True,
            'message': 'Payment recorded successfully!',
            'remaining_balance': new_balance
        })
        
    except Exception as e:
        print(f"Error adding payment: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'})
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """Get retailer settings API"""
    try:
        # Verify JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'message': 'Authentication required'})
        
        token = auth_header.split(' ')[1]
        retailer_id = verify_jwt_token(token)
        if not retailer_id:
            return jsonify({'success': False, 'message': 'Invalid or expired token'})
        
        db = get_db()
        
        # Get retailer info
        retailer = db.execute(
            'SELECT * FROM retailers WHERE id = ?',
            (retailer_id,)
        ).fetchone()
        
        if not retailer:
            return jsonify({'success': False, 'message': 'Retailer not found'})
        
        return jsonify({
            'success': True,
            'retailer': {
                'id': retailer['id'],
                'phone': retailer['phone'],
                'shop_name': retailer['shop_name'],
                'shop_address': retailer['shop_address'],
                'shop_photo_url': retailer['shop_photo_url'],
                'created_at': retailer['created_at']
            }
        })
        
    except Exception as e:
        print(f"Error getting settings: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'})
    finally:
        if 'db' in locals():
            db.close()

# ============================================================================ 
# RUN APPLICATION
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
