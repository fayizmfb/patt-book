"""
Patt Book - Retailer + Customer Credit System
FIXED: Phone-number based authentication with ledger system + Push Notifications
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from datetime import datetime, timedelta
from database import init_db, get_db
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
app.secret_key = 'your-secret-key-change-in-production'

# ============================================================================ 
# AUTHENTICATION HELPERS
# ============================================================================

def is_user_logged_in():
    """Check if user is logged in"""
    return 'user_id' in session

# ============================================================================ 
# PUSH NOTIFICATION HELPERS
# ============================================================================

def send_push_notification(customer_phone, title, message):
    """Send push notification to customer using FCM"""
    try:
        db = get_db()
        
        # Get customer's FCM token
        token_result = db.execute(
            'SELECT token FROM fcm_tokens WHERE customer_phone = ?',
            (customer_phone,)
        ).fetchone()
        
        if not token_result:
            print(f"No FCM token found for customer {customer_phone}")
            return False
        
        fcm_token = token_result['token']
        
        # In production, use your FCM server key
        fcm_server_key = os.environ.get('FCM_SERVER_KEY', 'your-fcm-server-key')
        
        # Prepare FCM request
        fcm_url = 'https://fcm.googleapis.com/fcm/send'
        headers = {
            'Authorization': f'key={fcm_server_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'to': fcm_token,
            'notification': {
                'title': title,
                'body': message,
                'sound': 'default',
                'click_action': 'FLUTTER_NOTIFICATION_CLICK'
            },
            'data': {
                'type': 'transaction_update',
                'customer_phone': customer_phone
            }
        }
        
        # Send notification
        response = requests.post(fcm_url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"Push notification sent successfully to {customer_phone}")
                return True
            else:
                print(f"FCM error: {result}")
                return False
        else:
            print(f"FCM request failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Push notification error: {e}")
        return False
    finally:
        if 'db' in locals():
            db.close()

def save_fcm_token(customer_phone, token):
    """Save FCM token for customer"""
    try:
        db = get_db()
        
        # Check if token already exists
        existing = db.execute(
            'SELECT id FROM fcm_tokens WHERE customer_phone = ? AND token = ?',
            (customer_phone, token)
        ).fetchone()
        
        if not existing:
            # Insert new token
            db.execute(
                'INSERT INTO fcm_tokens (customer_phone, token) VALUES (?, ?)',
                (customer_phone, token)
            )
        else:
            # Token exists, no action needed
            pass
        
        db.commit()
        print(f"FCM token saved for customer {customer_phone}")
        
    except Exception as e:
        print(f"Error saving FCM token: {e}")
        if 'db' in locals():
            db.rollback()
    finally:
        if 'db' in locals():
            db.close()

# ============================================================================ 
# ROUTES - CORE PATT BOOK FLOW
# ============================================================================

@app.route('/')
def home():
    """Root route - redirect to role selection"""
    return redirect(url_for('role_selection'))

@app.route('/role-selection')
def role_selection():
    """Role selection screen - First page users see"""
    return render_template('role_selection.html')

@app.route('/retailer/login', methods=['GET', 'POST'])
def retailer_login():
    """Retailer login - OTP based authentication"""
    if request.method == 'POST':
        phone = request.form.get('phone')
        
        if not phone:
            flash('Phone number is required', 'error')
            return render_template('retailer_login.html')
        
        # Clean phone number
        if not phone.startswith('+'):
            phone = '+' + phone
        
        db = get_db()
        try:
            # Check if retailer exists
            retailer = db.execute(
                'SELECT retailer_phone, shop_name FROM retailers WHERE retailer_phone = ?',
                (phone,)
            ).fetchone()
            
            if retailer:
                # OTP simulation - in production use Firebase OTP
                session['user_id'] = phone
                session['user_type'] = 'retailer'
                session['phone_number'] = phone
                session['shop_name'] = retailer['shop_name']
                
                flash('Login successful!', 'success')
                return redirect(url_for('retailer_dashboard'))
            else:
                flash('Phone number not found. Please create an account first.', 'error')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'error')
        finally:
            db.close()
    
    return render_template('retailer_login.html')

@app.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    """Customer login - OTP based authentication"""
    if request.method == 'POST':
        phone = request.form.get('phone')
        
        if not phone:
            flash('Phone number is required', 'error')
            return render_template('customer_login.html')
        
        # Clean phone number
        if not phone.startswith('+'):
            phone = '+' + phone
        
        db = get_db()
        try:
            # Check if customer exists
            customer = db.execute(
                'SELECT customer_phone, customer_name FROM customers WHERE customer_phone = ?',
                (phone,)
            ).fetchone()
            
            if customer:
                # OTP simulation - in production use Firebase OTP
                session['user_id'] = phone
                session['user_type'] = 'customer'
                session['phone_number'] = phone
                
                flash('Login successful!', 'success')
                return redirect(url_for('customer_dashboard'))
            else:
                flash('Phone number not found. Please create an account first.', 'error')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'error')
        finally:
            db.close()
    
    return render_template('customer_login.html')

@app.route('/retailer/register', methods=['GET', 'POST'])
def retailer_register():
    """Retailer registration - phone + shop name only"""
    if request.method == 'POST':
        shop_name = request.form.get('shop_name', '').strip()
        phone = request.form.get('phone', '').strip()
        shop_address = request.form.get('shop_address', '').strip()
        
        # Validation
        if not shop_name or not phone:
            flash('Shop name and phone number are required', 'error')
            return render_template('retailer_register.html')
        
        # Clean phone number
        if not phone.startswith('+'):
            phone = '+' + phone
        
        db = get_db()
        try:
            # Check if phone already exists
            existing = db.execute(
                'SELECT retailer_phone FROM retailers WHERE retailer_phone = ?',
                (phone,)
            ).fetchone()
            
            if existing:
                flash('A retailer with this phone number already exists!', 'error')
                return render_template('retailer_register.html')
            
            # Create retailer
            db.execute(
                'INSERT INTO retailers (retailer_phone, shop_name) VALUES (?, ?)',
                (phone, shop_name)
            )
            
            db.commit()
            
            print(f"Retailer registered successfully: Phone={phone}, Shop={shop_name}")
            flash('Retailer account created successfully! Please login.', 'success')
            return redirect(url_for('retailer_login'))
            
        except Exception as e:
            db.rollback()
            print(f"Error registering retailer: {str(e)}")
            flash(f'Error creating account: {str(e)}', 'error')
        finally:
            db.close()
    
    return render_template('retailer_register.html')

@app.route('/customer/register', methods=['GET', 'POST'])
def customer_register():
    """Customer registration - phone + name only"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        
        # Validation
        if not name or not phone:
            flash('Name and phone number are required', 'error')
            return render_template('customer_register.html')
        
        # Clean phone number
        if not phone.startswith('+'):
            phone = '+' + phone
        
        db = get_db()
        try:
            # Check if phone already exists
            existing = db.execute(
                'SELECT customer_phone FROM customers WHERE customer_phone = ?',
                (phone,)
            ).fetchone()
            
            if existing:
                flash('A customer with this phone number already exists!', 'error')
                return render_template('customer_register.html')
            
            # Create customer (no retailer linkage initially)
            db.execute(
                'INSERT INTO customers (customer_phone, customer_name, retailer_phone) VALUES (?, ?, ?)',
                (phone, name, 'temp_retailer')
            )
            
            db.commit()
            
            print(f"Customer registered successfully: Phone={phone}, Name={name}")
            flash('Customer account created successfully! Please login.', 'success')
            return redirect(url_for('customer_login'))
            
        except Exception as e:
            db.rollback()
            print(f"Error registering customer: {str(e)}")
            flash(f'Error creating account: {str(e)}', 'error')
        finally:
            db.close()
    
    return render_template('customer_register.html')

@app.route('/retailer/dashboard')
def retailer_dashboard():
    """Retailer dashboard - add customer, credit, payment"""
    if not is_user_logged_in():
        return redirect(url_for('retailer_login'))
    if session.get('user_type') != 'retailer':
        flash('Access denied', 'error')
        return redirect(url_for('retailer_login'))
        
    db = get_db()
    retailer_phone = session.get('phone_number')
    
    try:
        # Get retailer info
        retailer = db.execute(
            'SELECT * FROM retailers WHERE retailer_phone = ?',
            (retailer_phone,)
        ).fetchone()
        
        # Get customers for this retailer
        customers = db.execute(
            'SELECT * FROM customers WHERE retailer_phone = ? ORDER BY customer_name',
            (retailer_phone,)
        ).fetchall()
        
        # Get recent transactions
        transactions = db.execute(
            'SELECT * FROM transactions WHERE retailer_phone = ? ORDER BY date DESC LIMIT 10',
            (retailer_phone,)
        ).fetchall()
        
    except Exception as e:
        print(f"Error in retailer dashboard: {e}")
        flash('Error loading dashboard', 'error')
        customers = []
        transactions = []
    finally:
        db.close()
    
    return render_template('retailer_dashboard.html', 
                     retailer=retailer, 
                     customers=customers, 
                     transactions=transactions)

@app.route('/customer/dashboard')
def customer_dashboard():
    """Customer dashboard - store-wise credit summary"""
    if not is_user_logged_in():
        return redirect(url_for('customer_login'))
    if session.get('user_type') != 'customer':
        flash('Access denied', 'error')
        return redirect(url_for('customer_login'))
        
    db = get_db()
    customer_phone = session.get('phone_number')
    
    try:
        # Get customer info
        customer = db.execute(
            'SELECT * FROM customers WHERE customer_phone = ?',
            (customer_phone,)
        ).fetchone()
        
        # Calculate outstanding per retailer
        outstanding_by_retailer = db.execute("""
            SELECT 
                r.shop_name,
                r.retailer_phone,
                COALESCE(SUM(CASE WHEN t.type = 'credit' THEN t.amount ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN t.type = 'payment' THEN t.amount ELSE 0 END), 0) as outstanding
            FROM retailers r
            INNER JOIN transactions t ON r.retailer_phone = t.retailer_phone
            WHERE t.customer_phone = ?
            GROUP BY r.retailer_phone, r.shop_name
            HAVING outstanding > 0
            ORDER BY outstanding DESC
        """, (customer_phone,)).fetchall()
        
        total_outstanding = sum(r['outstanding'] for r in outstanding_by_retailer)
        
    except Exception as e:
        print(f"Error in customer dashboard: {e}")
        flash('Error loading dashboard', 'error')
        outstanding_by_retailer = []
        total_outstanding = 0
    finally:
        db.close()
    
    return render_template('customer_dashboard.html',
                     outstanding_by_retailer=outstanding_by_retailer,
                     total_outstanding=total_outstanding)

@app.route('/customer/retailer/<retailer_phone>')
def customer_retailer_detail(retailer_phone):
    """Customer retailer detail - transaction history"""
    if not is_user_logged_in():
        return redirect(url_for('customer_login'))
    if session.get('user_type') != 'customer':
        flash('Access denied', 'error')
        return redirect(url_for('customer_login'))
        
    db = get_db()
    customer_phone = session.get('phone_number')
    
    try:
        # Get retailer info
        retailer = db.execute(
            'SELECT * FROM retailers WHERE retailer_phone = ?',
            (retailer_phone,)
        ).fetchone()
        
        if not retailer:
            flash('Retailer not found', 'error')
            return redirect(url_for('customer_dashboard'))
        
        # Get transaction history
        transactions = db.execute("""
            SELECT type, amount, date, notes
            FROM transactions
            WHERE retailer_phone = ? AND customer_phone = ?
            ORDER BY date DESC
        """, (retailer_phone, customer_phone)).fetchall()
        
        # Calculate outstanding
        outstanding_result = db.execute("""
            SELECT COALESCE(SUM(CASE WHEN type = 'credit' THEN amount ELSE 0 END), 0) -
                   COALESCE(SUM(CASE WHEN type = 'payment' THEN amount ELSE 0 END), 0) as outstanding
            FROM transactions
            WHERE retailer_phone = ? AND customer_phone = ?
        """, (retailer_phone, customer_phone)).fetchone()
        
        outstanding = outstanding_result['outstanding'] if outstanding_result else 0
        
    except Exception as e:
        print(f"Error in customer retailer detail: {e}")
        flash('Error loading retailer details', 'error')
        retailer = None
        transactions = []
        outstanding = 0
    finally:
        db.close()
    
    return render_template('customer_retailer_detail.html',
                     retailer=retailer,
                     transactions=transactions,
                     outstanding=outstanding)

@app.route('/retailer/add-customer', methods=['GET', 'POST'])
def add_customer():
    """Add customer - can add with initial credit"""
    if not is_user_logged_in():
        return redirect(url_for('retailer_login'))
    if session.get('user_type') != 'retailer':
        flash('Access denied', 'error')
        return redirect(url_for('retailer_login'))
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        initial_credit = request.form.get('initial_credit', '').strip()
        
        if not name or not phone:
            flash('Customer name and phone are required', 'error')
            return render_template('add_customer.html')
        
        # Clean phone number
        if not phone.startswith('+'):
            phone = '+' + phone
        
        db = get_db()
        retailer_phone = session.get('phone_number')
        
        try:
            # Check if customer already exists
            existing = db.execute(
                'SELECT customer_phone FROM customers WHERE customer_phone = ?',
                (phone,)
            ).fetchone()
            
            if existing:
                flash('Customer with this phone number already exists!', 'error')
                return render_template('add_customer.html')
            
            # Create customer
            db.execute(
                'INSERT INTO customers (customer_phone, customer_name, retailer_phone) VALUES (?, ?, ?)',
                (phone, name, retailer_phone)
            )
            
            # If initial credit provided, create transaction
            if initial_credit and float(initial_credit) > 0:
                db.execute(
                    'INSERT INTO transactions (retailer_phone, customer_phone, type, amount, date, notes) VALUES (?, ?, ?, ?, ?, ?)',
                    (retailer_phone, phone, 'credit', float(initial_credit), datetime.now().date(), 'Initial credit')
                )
                
                # Send push notification
                retailer = db.execute(
                    'SELECT shop_name FROM retailers WHERE retailer_phone = ?',
                    (retailer_phone,)
                ).fetchone()
                
                if retailer:
                    title = f"{retailer['shop_name']} - Credit Added"
                    message = f"₹{float(initial_credit):.2f} credit has been added to your account"
                    send_push_notification(phone, title, message)
            
            db.commit()
            
            flash('Customer added successfully!', 'success')
            return redirect(url_for('retailer_dashboard'))
            
        except Exception as e:
            db.rollback()
            print(f"Error adding customer: {e}")
            flash(f'Error adding customer: {str(e)}', 'error')
        finally:
            db.close()
    
    return render_template('add_customer.html')

@app.route('/retailer/add-transaction', methods=['GET', 'POST'])
def add_transaction():
    """Add credit or payment transaction"""
    if not is_user_logged_in():
        return redirect(url_for('retailer_login'))
    if session.get('user_type') != 'retailer':
        flash('Access denied', 'error')
        return redirect(url_for('retailer_login'))
        
    if request.method == 'POST':
        customer_phone = request.form.get('customer_phone')
        trans_type = request.form.get('type')
        amount = request.form.get('amount')
        notes = request.form.get('notes', '')
        
        if not customer_phone or not trans_type or not amount:
            flash('Customer, type, and amount are required', 'error')
            return render_template('add_transaction.html')
        
        db = get_db()
        retailer_phone = session.get('phone_number')
        
        try:
            # Create transaction
            db.execute(
                'INSERT INTO transactions (retailer_phone, customer_phone, type, amount, date, notes) VALUES (?, ?, ?, ?, ?, ?)',
                (retailer_phone, customer_phone, trans_type, float(amount), datetime.now().date(), notes)
            )
            
            # Send push notification
            retailer = db.execute(
                'SELECT shop_name FROM retailers WHERE retailer_phone = ?',
                (retailer_phone,)
            ).fetchone()
            
            if retailer:
                if trans_type == 'credit':
                    title = f"{retailer['shop_name']} - Credit Added"
                    message = f"₹{float(amount):.2f} credit has been added to your account"
                else:
                    title = f"{retailer['shop_name']} - Payment Recorded"
                    message = f"₹{float(amount):.2f} payment has been recorded"
                
                send_push_notification(customer_phone, title, message)
            
            db.commit()
            
            flash(f'{trans_type.title()} added successfully!', 'success')
            return redirect(url_for('retailer_dashboard'))
            
        except Exception as e:
            db.rollback()
            print(f"Error adding transaction: {e}")
            flash(f'Error adding transaction: {str(e)}', 'error')
        finally:
            db.close()
    
    return render_template('add_transaction.html')

@app.route('/customer/save-fcm-token', methods=['POST'])
def save_fcm_token_endpoint():
    """Save FCM token for push notifications"""
    if not is_user_logged_in():
        return {'success': False, 'message': 'Not logged in'}, 401
    
    if session.get('user_type') != 'customer':
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    if not data or not data.get('token'):
        return {'success': False, 'message': 'Token required'}, 400
    
    customer_phone = session.get('phone_number')
    token = data.get('token')
    
    if save_fcm_token(customer_phone, token):
        return {'success': True, 'message': 'Token saved successfully'}
    else:
        return {'success': False, 'message': 'Failed to save token'}, 500

@app.route('/logout')
def logout():
    """Logout - clear session and return to role selection"""
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('role_selection'))

@app.route('/health')
def health_check():
    """Health check for monitoring"""
    return {"status": "ok", "message": "Patt Book backend is running"}

# ============================================================================ 
# INITIALIZE DATABASE
# ============================================================================

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
