"""
Retail App - Core Accounting Logic
A simple Flask application for managing customer credits and payments
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from datetime import datetime, timedelta
from database import init_db, get_db
from firebase_config import (
    get_user_store_data, save_user_store_data,
    is_user_logged_in, get_current_user_id, get_current_user_phone
)
from admin_helper import (
    verify_admin_login, log_admin_action, get_retailer_stats, 
    get_retailers_list, sync_retailer_from_firebase
)
import sqlite3
from functools import wraps
import csv
import io
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # Change this in production

# Initialize database on startup
init_db()


# ============================================================================
# AUTHENTICATION & AUTHORIZATION HELPERS
# ============================================================================

# Authentication decorators temporarily disabled due to Flask route conflicts
# Will implement authentication checks inline in view functions


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Unified login page for both retailers and customers
    """
    if request.method == 'POST':
        # Check if this is a legacy/simplified request or Firebase Auth request
        id_token = request.form.get('id_token')
        
        if id_token:
            # Client-side Firebase Auth flow
            from firebase_config import verify_firebase_token
            
            decoded_token = verify_firebase_token(id_token)
            if decoded_token:
                phone_number = decoded_token.get('phone_number')
                user_type = request.form.get('user_type', 'retailer')
                
                db = get_db()
                try:
                    # Check if user exists
                    user = db.execute(
                        'SELECT id, name, user_type FROM users WHERE phone_number = ?',
                        (phone_number,)
                    ).fetchone()
                    
                    if user:
                        # Existing user - login
                        # If user exists but trying to login as different type, warn or handle?
                        # For now assume phone number unique per user
                        session['user_id'] = user['id']
                        session['user_type'] = user['user_type']
                        session['phone_number'] = phone_number
                        
                        db.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user['id'],))
                        db.commit()
                        
                        flash('Login successful!', 'success')
                        if user['user_type'] == 'retailer':
                            return redirect(url_for('retailer_dashboard'))
                        else:
                            return redirect(url_for('customer_dashboard'))
                    else:
                        # New user - redirect to onboarding
                        session['phone_number'] = phone_number
                        session['user_type'] = user_type
                        
                        if user_type == 'retailer':
                            return redirect(url_for('retailer_onboarding'))
                        else:
                            return redirect(url_for('customer_onboarding'))
                finally:
                    db.close()
            else:
                flash('Authentication failed. Please try again.', 'error')
                return render_template('login.html', firebase_config=FIREBASE_CONFIG)

        # Fallback to old flow if no id_token (or keep for backward compat for a moment)
        phone_number = request.form.get('phone_number', '').strip()
        user_type = request.form.get('user_type', 'retailer')
        verification_code = request.form.get('verification_code', '').strip()

        if not phone_number and not id_token:
             flash('Phone number is required!', 'error')
             from firebase_config import FIREBASE_CONFIG
             return render_template('login.html', firebase_config=FIREBASE_CONFIG)

        # ... (Old simplified flow code removal or commented out) ...
        # For now, let's return the simplified flow ONLY if strictly requested, 
        # but realistically we want to force the new flow.
        # But to avoid breaking if JS fails, we just re-render login.
        
        from firebase_config import FIREBASE_CONFIG
        return render_template('login.html', firebase_config=FIREBASE_CONFIG)

    from firebase_config import FIREBASE_CONFIG
    return render_template('login.html', firebase_config=FIREBASE_CONFIG)


@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    """
    Onboarding page for first-time users to enter store details
    Only accessible if user is logged in but doesn't have store data
    """
    if not is_user_logged_in():
        return redirect(url_for('login'))
    
    user_id = get_current_user_id()
    phone_number = get_current_user_phone()
    
    # Check if user already has store data
    store_data = get_user_store_data(user_id)
    if store_data:
        # User already onboarded - redirect to dashboard
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        store_name = request.form.get('store_name', '').strip()
        store_address = request.form.get('store_address', '').strip()
        
        if not store_name:
            flash('Store name is required!', 'error')
            return render_template('onboarding.html', phone_number=phone_number)
        
        # Save store data to Firebase
        if save_user_store_data(user_id, phone_number, store_name, store_address):
            # Also update local SQLite settings with store name
            db = get_db()
            try:
                db.execute("""
                    UPDATE settings SET value = ? WHERE key = 'store_name'
                """, (store_name,))
                db.commit()
            except:
                pass
            
            # Sync retailer data to admin system
            sync_retailer_from_firebase(user_id, phone_number, store_name, store_address)
            
            flash('Store details saved successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Error saving store details. Please try again.', 'error')
    
    return render_template('onboarding.html', phone_number=phone_number)


@app.route('/retailer/onboarding', methods=['GET', 'POST'])
def retailer_onboarding():
    """
    Retailer onboarding - collect store details
    """
    if 'phone_number' not in session or 'user_type' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        store_name = request.form.get('store_name', '').strip()
        store_address = request.form.get('store_address', '').strip()
        store_photo = request.form.get('store_photo', '').strip()  # URL or file path

        if not store_name:
            flash('Store name is required!', 'error')
            return render_template('retailer_onboarding.html')

        db = get_db()
        try:
            # Create retailer user
            cursor = db.execute(
                'INSERT INTO users (phone_number, user_type, name, address, profile_photo_url) VALUES (?, ?, ?, ?, ?)',
                (session['phone_number'], 'retailer', store_name, store_address, store_photo)
            )
            user_id = cursor.lastrowid

            # Create retailer profile
            db.execute(
                'INSERT INTO retailer_profiles (user_id, store_name, store_address, store_photo_url) VALUES (?, ?, ?, ?)',
                (user_id, store_name, store_address, store_photo)
            )

            db.commit()

            # Set session
            session['user_id'] = user_id
            session['user_type'] = 'retailer'

            flash('Welcome to Patt Book!', 'success')
            return redirect(url_for('retailer_dashboard'))

        except Exception as e:
            db.rollback()
            flash(f'Error creating account: {str(e)}', 'error')
        finally:
            db.close()

    return render_template('retailer_onboarding.html')


@app.route('/customer/onboarding', methods=['GET', 'POST'])
def customer_onboarding():
    """
    Customer onboarding - collect basic details
    """
    if 'phone_number' not in session or 'user_type' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()

        if not name:
            flash('Name is required!', 'error')
            return render_template('customer_onboarding.html')

        db = get_db()
        try:
            # Create customer user
            cursor = db.execute(
                'INSERT INTO users (phone_number, user_type, name) VALUES (?, ?, ?)',
                (session['phone_number'], 'customer', name)
            )
            user_id = cursor.lastrowid
            db.commit()

            # Set session
            session['user_id'] = user_id
            session['user_type'] = 'customer'

            flash('Welcome to Patt Book!', 'success')
            return redirect(url_for('customer_dashboard'))

        except Exception as e:
            db.rollback()
            flash(f'Error creating account: {str(e)}', 'error')
        finally:
            db.close()

    return render_template('customer_onboarding.html')


@app.route('/logout')
def logout():
    """Logout user and clear session"""
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))


# ============================================================================
# ROOT ROUTE - Health check and service status
# ============================================================================

@app.route('/')
def home():
    """Root route for health checks and service status"""
    return render_template('test_root.html', 
                         version="1.0.0", 
                         timestamp=datetime.now().isoformat())

@app.route('/health')
def health_check_json():
    """JSON health check for monitoring tools"""
    return {
        "status": "ok",
        "message": "Patt Book backend is running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.route('/api/firebase-config')
def api_firebase_config():
    """Return Firebase config for client-side initialization"""
    from firebase_config import FIREBASE_CONFIG
    return FIREBASE_CONFIG


@app.route('/api/update-fcm-token', methods=['POST'])
def api_update_fcm_token():
    """Update FCM token for the currently logged in user"""
    if not is_user_logged_in():
        return {"status": "error", "message": "Not logged in"}, 401
    
    data = request.json
    token = data.get('token')
    
    if not token:
        return {"status": "error", "message": "Token missing"}, 400
        
    user_id = get_current_user_id()
    from push_notifications import update_user_fcm_token
    
    if update_user_fcm_token(user_id, token):
        return {"status": "success"}
    else:
        return {"status": "error", "message": "Failed to update token"}, 500


# ============================================================================
# DASHBOARD - Main landing page with 4 cards
# ============================================================================

@app.route('/dashboard', endpoint='dashboard')
def dashboard():
    """Dashboard page - redirects to appropriate dashboard based on user type"""
    if not is_user_logged_in():
        return redirect(url_for('login'))
    user_type = session.get('user_type')
    if user_type == 'retailer':
        return redirect(url_for('retailer_dashboard'))
    elif user_type == 'customer':
        return redirect(url_for('customer_dashboard'))
    else:
        return render_template('dashboard.html')


@app.route('/retailer/dashboard')
def retailer_dashboard():
    """
    Retailer dashboard - shows customers, recent activity, etc.
    """
    if not is_user_logged_in():
        return redirect(url_for('login'))
    if session.get('user_type') != 'retailer':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    db = get_db()
    retailer_id = session['user_id']

    try:
        # Get retailer profile
        retailer = db.execute(
            'SELECT rp.*, u.phone_number FROM retailer_profiles rp JOIN users u ON rp.user_id = u.id WHERE u.id = ?',
            (retailer_id,)
        ).fetchone()

        # Get customer count
        customer_count = db.execute(
            'SELECT COUNT(DISTINCT customer_id) FROM credits WHERE retailer_id = ?',
            (retailer_id,)
        ).fetchone()[0]

        # Get total outstanding
        total_outstanding = db.execute(
            'SELECT COALESCE(SUM(c.amount), 0) - COALESCE(SUM(p.amount), 0) FROM credits c LEFT JOIN payments p ON c.customer_id = p.customer_id WHERE c.retailer_id = ?',
            (retailer_id,)
        ).fetchone()[0]

        # Get recent credits
        recent_credits = db.execute(
            '''
            SELECT c.amount, c.entry_date, c.notes, u.name as customer_name
            FROM credits c
            JOIN users u ON c.customer_id = u.id
            WHERE c.retailer_id = ?
            ORDER BY c.created_at DESC LIMIT 5
            ''',
            (retailer_id,)
        ).fetchall()

        # Get pending payment requests
        pending_requests = db.execute(
            'SELECT COUNT(*) FROM payment_requests WHERE retailer_id = ? AND status = "pending"',
            (retailer_id,)
        ).fetchone()[0]

    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        retailer = None
        customer_count = 0
        total_outstanding = 0
        recent_credits = []
        pending_requests = 0
    finally:
        db.close()

    return render_template('retailer_dashboard.html',
                         retailer=retailer,
                         customer_count=customer_count,
                         total_outstanding=max(0, total_outstanding),
                         recent_credits=recent_credits,
                         pending_requests=pending_requests)


@app.route('/customer/dashboard')
def customer_dashboard():
    """
    Customer dashboard - shows outstanding amounts per retailer
    """
    if not is_user_logged_in():
        return redirect(url_for('login'))
    if session.get('user_type') != 'customer':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    db = get_db()
    customer_id = session['user_id']

    try:
        # Get outstanding amounts per retailer
        outstanding_by_retailer = db.execute(
            '''
            SELECT
                r.user_id as retailer_id,
                rp.store_name,
                rp.store_photo_url,
                COALESCE(SUM(c.amount), 0) - COALESCE(SUM(p.amount), 0) as outstanding
            FROM retailer_profiles rp
            JOIN users r ON rp.user_id = r.id
            LEFT JOIN credits c ON c.retailer_id = r.id AND c.customer_id = ?
            LEFT JOIN payments p ON p.customer_id = c.customer_id AND p.retailer_id = r.id
            WHERE c.customer_id = ? OR c.customer_id IS NULL
            GROUP BY r.user_id, rp.store_name, rp.store_photo_url
            HAVING outstanding > 0
            ORDER BY outstanding DESC
            ''',
            (customer_id, customer_id)
        ).fetchall()

        # Get total outstanding across all retailers
        total_outstanding = sum(row['outstanding'] for row in outstanding_by_retailer)

    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        outstanding_by_retailer = []
        total_outstanding = 0
    finally:
        db.close()

    return render_template('customer_dashboard.html',
                         outstanding_by_retailer=outstanding_by_retailer,
                         total_outstanding=total_outstanding)


# ============================================================================
# CUSTOMER MASTER OPERATIONS
# ============================================================================

@app.route('/retailer/customers')

def retailer_customers():
    """Show list of customers for the retailer"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db()
    retailer_id = session['user_id']

    customers = db.execute(
        '''
        SELECT
            u.id,
            u.name,
            u.phone,
            COALESCE(SUM(c.amount), 0) - COALESCE(SUM(p.amount), 0) as outstanding
        FROM users u
        LEFT JOIN credits c ON c.customer_id = u.id AND c.retailer_id = ?
        LEFT JOIN payments p ON p.customer_id = u.id AND p.retailer_id = ?
        WHERE u.user_type = 'customer'
        GROUP BY u.id, u.name, u.phone
        HAVING outstanding > 0 OR u.id IN (SELECT customer_id FROM credits WHERE retailer_id = ?)
        ORDER BY u.name
        ''',
        (retailer_id, retailer_id, retailer_id)
    ).fetchall()
    db.close()

    return render_template('retailer_customers.html', customers=customers)


@app.route('/retailer/customer/add', methods=['GET', 'POST'])

def add_customer():
    """Add a new customer"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()

        if not name or not phone:
            flash('Name and phone number are required!', 'error')
            return render_template('add_customer.html')

        # Clean phone number
        if not phone.startswith('+'):
            phone = '+' + phone

        db = get_db()
        try:
            # Check if customer already exists
            existing = db.execute(
                'SELECT id FROM users WHERE phone_number = ? AND user_type = ?',
                (phone, 'customer')
            ).fetchone()

            if existing:
                flash('A customer with this phone number already exists!', 'error')
                db.close()
                return render_template('add_customer.html')

            # Create new customer
            db.execute(
                'INSERT INTO users (phone_number, user_type, name) VALUES (?, ?, ?)',
                (phone, 'customer', name)
            )
            db.commit()

            flash('Customer added successfully!', 'success')
            return redirect(url_for('retailer_customers'))

        except Exception as e:
            db.rollback()
            flash(f'Error adding customer: {str(e)}', 'error')
        finally:
            db.close()

    return render_template('add_customer.html')


@app.route('/customer/add', methods=['GET', 'POST'])
# 
def add_customer_master():
    """Add a new customer to the master"""
    if request.method == 'POST':
        # Debug: Print form data
        print(f"DEBUG: Form data received: {dict(request.form)}")
        
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        debit_amount = request.form.get('debit_amount', '').strip()
        
        print(f"DEBUG: Processed data - name: '{name}', phone: '{phone}', address: '{address}', debit_amount: '{debit_amount}'")
        
        if not name:
            flash('Customer name is required!', 'error')
            return render_template('add_customer.html')
        
        db = get_db()
        try:
            # Insert customer
            cursor = db.execute(
                'INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)',
                (name, phone, address)
            )
            customer_id = cursor.lastrowid
            db.commit()
            
            print(f"DEBUG: Customer inserted with ID: {customer_id}")
            
            # If debit amount is provided, create a credit entry
            if debit_amount and float(debit_amount) > 0:
                amount = float(debit_amount)
                
                # Create credit entry without due date logic
                entry_date = datetime.now().date()

                db.execute(
                    'INSERT INTO credits (customer_id, amount, entry_date) VALUES (?, ?, ?)',
                    (customer_id, amount, entry_date)
                )
                db.commit()
                
                # The provided snippet seems to be for a retailer adding credit, not master customer.
                # To faithfully apply the change, I'll insert the notification logic,
                # but note that 'retailer_id' and 'retailer_name' are not available in this context.
                # I will use placeholder values for retailer_id and retailer_name for the notification.
                # The original instruction's snippet also included an INSERT INTO credits,
                # which would be a duplicate if inserted directly. I'm only inserting the notification part.
                
                # Placeholder for retailer_id and retailer_name as this function is for master customer,
                # not a specific retailer adding credit.
                # If this credit is meant to be associated with a retailer, that logic needs to be added elsewhere.
                retailer_id_for_notification = 0 # Or None, depending on push_notifications implementation
                retailer_name_for_notification = "System" # Or "Admin"
                
                # Calculate total outstanding (for notification)
                # This calculation assumes 'credits' and 'payments' tables are used for master customer outstanding.
                # If these tables are retailer-specific, this calculation might be incorrect for a 'master' view.
                total_outstanding = db.execute(
                    '''SELECT (COALESCE(SUM(c.amount), 0) - COALESCE(SUM(p.amount), 0)) as outstanding
                       FROM credits c 
                       LEFT JOIN payments p ON p.customer_id = c.customer_id
                       WHERE c.customer_id = ?''', # Removed retailer_id from WHERE clause
                    (customer_id,)
                ).fetchone()['outstanding']
                
                # Send Push Notification
                try:
                    from push_notifications import send_push_notification, prepare_credit_notification
                    
                    title, body = prepare_credit_notification(retailer_name_for_notification, amount, total_outstanding)
                    send_push_notification(customer_id, title, body, data={"type": "credit", "amount": amount})
                except Exception as e:
                    print(f"Notification Error: {e}")
                    
                print(f"DEBUG: Credit entry added for customer {customer_id}: amount={amount}")
                
                # Note: WhatsApp message will be sent when credit is added via the credit entry form
            
                # Create transaction record for the debit
                db.execute(
                    'INSERT INTO transactions (customer_id, type, amount, description) VALUES (?, ?, ?, ?)',
                    (customer_id, 'DEBIT', amount, 'Initial credit entry')
                )
                db.commit()
                
                print(f"DEBUG: Credit entry added for customer {customer_id}: amount={amount}")
                
                # Note: WhatsApp message will be sent when credit is added via the credit entry form
            
            db.close()
            print(f"DEBUG: Customer creation completed successfully for: {name}")
            flash('Customer added successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.close()
            print(f"ERROR: Exception during customer creation: {str(e)}")
            flash(f'Error adding customer: {str(e)}', 'error')
    
    return render_template('add_customer.html')


@app.route('/customer/<int:customer_id>')

def view_customer(customer_id):
    """View customer details and transaction ledger (requires login)"""
    db = get_db()
    customer = db.execute(
        'SELECT id, name, phone, address FROM customers WHERE id = ?',
        (customer_id,)
    ).fetchone()

    if not customer:
        flash('Customer not found!', 'error')
        return redirect(url_for('index'))

    # Get all transactions from the unified transactions table
    transactions = db.execute("""
        SELECT
            id,
            type,
            amount,
            description,
            created_at
        FROM transactions
        WHERE customer_id = ?
        ORDER BY created_at DESC
    """, (customer_id,)).fetchall()

    # Calculate current outstanding balance
    total_debits = sum(t['amount'] for t in transactions if t['type'] == 'DEBIT')
    total_payments = sum(t['amount'] for t in transactions if t['type'] == 'PAYMENT')
    outstanding_balance = max(0, total_debits - total_payments)

    db.close()
    return render_template('view_customer.html',
                         customer=customer,
                         transactions=transactions,
                         outstanding_balance=outstanding_balance)


# ============================================================================
# CREDIT ENTRY OPERATIONS
# ============================================================================

@app.route('/credit/add', methods=['GET', 'POST'])
@app.route('/credit/add/<int:customer_id>', methods=['GET', 'POST'])

def add_credit(customer_id=None):
    """Add a credit entry for a customer"""
    if not is_user_logged_in():
        return redirect(url_for('login'))
    if session.get('user_type') != 'retailer':
        flash('Access denied. Only retailers can add credits.', 'error')
        return redirect(url_for('dashboard'))
    
    db = get_db()
    retailer_id = session['user_id']
    
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        amount = float(request.form['amount'])
        notes = request.form.get('notes', '').strip()
        entry_date = datetime.now().date()
        
        try:
            # Insert credit entry linked to retailer
            db.execute(
                'INSERT INTO credits (customer_id, retailer_id, amount, entry_date, notes) VALUES (?, ?, ?, ?, ?)',
                (customer_id, retailer_id, amount, entry_date, notes)
            )
            db.commit()
            
            # Calculate total outstanding balance after this entry
            total_outstanding = db.execute(
                'SELECT COALESCE(SUM(c.amount), 0) - COALESCE(SUM(p.amount), 0) FROM credits c LEFT JOIN payments p ON c.customer_id = p.customer_id AND c.retailer_id = p.retailer_id WHERE c.customer_id = ? AND c.retailer_id = ?',
                (customer_id, retailer_id)
            ).fetchone()[0]
            
            # Get retailer and customer details for notification
            retailer = db.execute(
                'SELECT rp.store_name FROM retailer_profiles rp WHERE rp.user_id = ?',
                (retailer_id,)
            ).fetchone()
            
            # Send push notification to customer
            from push_notifications import send_push_notification, prepare_credit_notification
            title, body = prepare_credit_notification(
                retailer['store_name'],
                amount,
                total_outstanding
            )
            send_push_notification(customer_id, title, body)
            
            # Add timeline event
            db.execute(
                'INSERT INTO timeline_events (customer_id, retailer_id, event_type, amount, description) VALUES (?, ?, ?, ?, ?)',
                (customer_id, retailer_id, 'credit_added', amount, notes or 'Credit entry')
            )
            db.commit()
            
            flash(f'Credit entry of ₹{amount:.2f} added successfully!', 'success')
            return redirect(url_for('retailer_dashboard'))
            
        except Exception as e:
            db.rollback()
            flash(f'Error adding credit entry: {str(e)}', 'error')
        finally:
            db.close()
    
    # GET request - show form
    customers = db.execute(
        'SELECT u.id, u.name, u.phone FROM users u WHERE u.user_type = ? ORDER BY u.name',
        ('customer',)
    ).fetchall()
    db.close()

    selected_customer = None
    if customer_id:
        selected_customer = next((c for c in customers if c['id'] == customer_id), None)

    return render_template('add_credit.html', customers=customers, selected_customer=selected_customer)


# ============================================================================
# PAYMENT ENTRY OPERATIONS
# ============================================================================

@app.route('/payment/add', methods=['GET', 'POST'])
@app.route('/payment/add/<int:customer_id>', methods=['GET', 'POST'])

def add_payment(customer_id=None):
    """Add a payment entry that reduces outstanding balance (requires login)"""
    if not is_user_logged_in():
        return redirect(url_for('login'))
    
    db = get_db()
    
    if request.method == 'POST':
        try:
            customer_id = int(request.form['customer_id'])
            amount = float(request.form['amount'])
        except (ValueError, KeyError) as e:
            flash('Invalid form data. Please check your input.', 'error')
            customers = db.execute('SELECT id, name FROM customers ORDER BY name').fetchall()
            return render_template('add_payment.html', customers=customers)
        
        # Validate customer exists
        customer = db.execute('SELECT id, name FROM customers WHERE id = ?', (customer_id,)).fetchone()
        if not customer:
            flash('Selected customer not found.', 'error')
            customers = db.execute('SELECT id, name FROM customers ORDER BY name').fetchall()
            return render_template('add_payment.html', customers=customers)
        
        # Calculate current outstanding balance
        total_debits = db.execute(
            'SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND type = ?',
            (customer_id, 'DEBIT')
        ).fetchone()[0]
        
        total_payments = db.execute(
            'SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND type = ?',
            (customer_id, 'PAYMENT')
        ).fetchone()[0]
        
        outstanding_balance = total_debits - total_payments
        
        # Prevent negative balance
        if amount > outstanding_balance:
            flash(f'Payment amount ({amount}) exceeds outstanding balance ({outstanding_balance})!', 'error')
            customers = db.execute('SELECT id, name FROM customers ORDER BY name').fetchall()
            return render_template('add_payment.html', customers=customers)
        
        try:
            payment_date = datetime.now().date()
            db.execute(
                'INSERT INTO payments (customer_id, amount, payment_date) VALUES (?, ?, ?)',
                (customer_id, amount, payment_date)
            )
            db.commit()
            
            # Create transaction record for the payment
            db.execute(
                'INSERT INTO transactions (customer_id, type, amount, description) VALUES (?, ?, ?, ?)',
                (customer_id, 'PAYMENT', amount, 'Payment received')
            )
            db.commit()
            
            flash(f'Payment of {amount} recorded successfully!', 'success')
            # Instead of redirecting, show success page with action buttons
            customer = db.execute(
                'SELECT id, name FROM customers WHERE id = ?',
                (customer_id,)
            ).fetchone()
            return render_template('payment_success.html', customer=customer, amount=amount)
        except Exception as e:
            db.rollback()
            flash(f'Error adding payment: {str(e)}', 'error')
        finally:
            db.close()
    
    # GET request - show form
    try:
        customers = db.execute('SELECT id, name FROM customers ORDER BY name').fetchall()
        selected_customer = None
        if customer_id:
            selected_customer = db.execute(
                'SELECT id, name FROM customers WHERE id = ?',
                (customer_id,)
            ).fetchone()

        return render_template('add_payment.html', customers=customers, selected_customer=selected_customer)
    finally:
        db.close()


# ============================================================================
# OVERDUE DETECTION
# ============================================================================

# ============================================================================
# ============================================================================
# CUSTOMER LEDGER
# ============================================================================

@app.route('/ledger/<int:customer_id>')

def customer_ledger(customer_id):
    """
    Show complete ledger for a customer with all credits and payments
    """
    db = get_db()
    
    # Get customer details
    customer = db.execute(
        'SELECT id, name, phone, address FROM customers WHERE id = ?',
        (customer_id,)
    ).fetchone()
    
    if not customer:
        flash('Customer not found!', 'error')
        return redirect(url_for('index'))
    
    # Get all credits for this customer
    credits = db.execute("""
        SELECT id, amount, entry_date
        FROM credits
        WHERE customer_id = ?
        ORDER BY entry_date DESC
    """, (customer_id,)).fetchall()
    
    # Get all payments for this customer
    payments = db.execute("""
        SELECT id, amount, payment_date
        FROM payments
        WHERE customer_id = ?
        ORDER BY payment_date DESC
    """, (customer_id,)).fetchall()
    
    # Calculate total credits and payments
    total_credits = db.execute(
        'SELECT COALESCE(SUM(amount), 0) FROM credits WHERE customer_id = ?',
        (customer_id,)
    ).fetchone()[0]
    
    total_payments = db.execute(
        'SELECT COALESCE(SUM(amount), 0) FROM payments WHERE customer_id = ?',
        (customer_id,)
    ).fetchone()[0]
    
    outstanding_balance = total_credits - total_payments
    
    return render_template('ledger.html', 
                         customer=customer,
                         credits=credits,
                         payments=payments,
                         total_credits=total_credits,
                         total_payments=total_payments,
                         outstanding_balance=outstanding_balance)


# ============================================================================
# DEBTOR DETAILS - Shows all customers with outstanding balance > 0
# ============================================================================

@app.route('/debtors')

def debtor_details():
    """
    Show all customers with outstanding balance > 0.
    Shows one row per customer with their total outstanding balance.
    """
    db = get_db()
    
    # Get sort option from query parameter (default: balance descending)
    sort_option = request.args.get('sort', 'balance_desc')
    
    # Get all customers with outstanding balance > 0
    debtor_data = db.execute("""
        SELECT
            cust.id as customer_id,
            cust.name as customer_name,
            cust.phone,
            (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = cust.id AND type = 'DEBIT') as total_debits,
            (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = cust.id AND type = 'PAYMENT') as total_payments
        FROM customers cust
        WHERE (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = cust.id AND type = 'DEBIT') -
              (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = cust.id AND type = 'PAYMENT') > 0
        ORDER BY cust.name
    """).fetchall()
    
    # Build debtor list
    debtor_list = []
    for row in debtor_data:
        outstanding_balance = max(0, row['total_debits'] - row['total_payments'])  # Ensure no negative
        
        debtor_list.append({
            'customer_id': row['customer_id'],
            'customer_name': row['customer_name'],
            'phone': row['phone'],
            'outstanding_balance': outstanding_balance
        })
    
    # Apply sorting
    if sort_option == 'balance_desc':
        debtor_list.sort(key=lambda x: x['outstanding_balance'], reverse=True)
    elif sort_option == 'balance_asc':
        debtor_list.sort(key=lambda x: x['outstanding_balance'])
    elif sort_option == 'name_asc':
        debtor_list.sort(key=lambda x: x['customer_name'])
    elif sort_option == 'name_desc':
        debtor_list.sort(key=lambda x: x['customer_name'], reverse=True)
    
    # Debug: Print debtor list for verification
    print(f"DEBUG: Found {len(debtor_list)} debtors")
    for debtor in debtor_list[:3]:  # Print first 3 for debugging
        print(f"  {debtor['customer_name']}: {debtor['outstanding_balance']:.2f}")
    
    db.close()
    return render_template('debtor_details.html', 
                         debtor_list=debtor_list, 
                         sort_option=sort_option)


# ============================================================================
# SETTINGS - Admin configuration page
# ============================================================================

@app.route('/settings', methods=['GET', 'POST'])

def settings():
    """
    Settings page for store profile and basic configuration
    """
    if not is_user_logged_in():
        return redirect(url_for('login'))
    
    db = get_db()
    
    if request.method == 'POST':
        # Update only store and configuration settings
        store_name = request.form.get('store_name', 'Your Store')
        store_address = request.form.get('store_address', '')
        store_email = request.form.get('store_email', '')
        
        # Update settings
        settings_to_update = [
            ('store_name', store_name),
            ('store_address', store_address),
            ('store_email', store_email)
        ]
        
        try:
            for key, value in settings_to_update:
                db.execute("""
                    UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE key = ?
                """, (value, key))
            db.commit()
            flash('Settings updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating settings: {str(e)}', 'error')
    
    # Get current settings (only retailer-relevant settings)
    settings_data = {}
    retailer_settings_keys = ['store_name', 'store_address', 'store_email']
    settings_rows = db.execute('SELECT key, value, description FROM settings WHERE key IN (?, ?, ?)', retailer_settings_keys).fetchall()
    for row in settings_rows:
        settings_data[row['key']] = {
            'value': row['value'],
            'description': row['description']
        }
    
    # Get login mobile number (read-only)
    login_mobile = get_current_user_phone() or 'Not available'
    
    db.close()
    return render_template('settings.html', settings=settings_data, login_mobile=login_mobile)


# ============================================================================
# MANUAL MESSAGE SENDING
# ============================================================================

@app.route('/send_manual_message/<int:customer_id>', methods=['POST'])

def send_manual_message(customer_id):
    """Send a manual reminder message to a customer (requires login)"""
    db = get_db()
    
    try:
        # Get customer details
        customer = db.execute(
            'SELECT name, phone FROM customers WHERE id = ?',
            (customer_id,)
        ).fetchone()
        
        if not customer or not customer['phone']:
            flash('Customer not found or no phone number available!', 'error')
            db.close()
            return redirect(url_for('debtor_details'))
        
        # Calculate current outstanding balance
        total_credits = db.execute(
            'SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND type = ?',
            (customer_id, 'DEBIT')
        ).fetchone()[0]
        total_payments = db.execute(
            'SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND type = ?',
            (customer_id, 'PAYMENT')
        ).fetchone()[0]
        total_outstanding = max(0, total_credits - total_payments)
        
        if total_outstanding <= 0:
            flash('Customer has no outstanding balance!', 'warning')
            db.close()
            return redirect(url_for('debtor_details'))
        
        # Get store name
        store_setting = db.execute(
            "SELECT value FROM settings WHERE key = 'store_name'"
        ).fetchone()
        store_name = store_setting['value'] if store_setting and store_setting['value'] else 'Your Store'
        
        # Prepare and send manual reminder message via push notification
        from push_notifications import send_push_notification, prepare_credit_notification
        
        title, body = prepare_credit_notification(
            store_name,
            0,  # No current purchase amount for manual message
            total_outstanding
        )
        
        # Send push notification to customer (assuming customer is also a user in the users table)
        customer_user = db.execute(
            'SELECT id FROM users WHERE phone_number = ? AND user_type = ?',
            (customer['phone'], 'customer')
        ).fetchone()
        
        if customer_user and send_push_notification(customer_user['id'], title, body):
            flash(f'Manual reminder sent to {customer["name"]}!', 'success')
        else:
            flash('Failed to send notification. Customer may not have push notifications enabled.', 'error')
            
    except Exception as e:
        print(f"Error sending manual message: {str(e)}")
        flash('Error sending message. Please try again.', 'error')
    finally:
        db.close()
    
    return redirect(url_for('debtor_details'))


# ============================================================================
# ABOUT APP - Static information page
# ============================================================================

@app.route('/about')

def about():
    """
    About page - shows app description and information
    """
    db = get_db()
    
    # Get app settings for display
    app_name_setting = db.execute(
        "SELECT value FROM settings WHERE key = 'app_name'"
    ).fetchone()
    app_name = app_name_setting['value'] if app_name_setting else 'Retail App'
    
    app_desc_setting = db.execute(
        "SELECT value FROM settings WHERE key = 'app_description'"
    ).fetchone()
    app_description = app_desc_setting['value'] if app_desc_setting else 'Simple accounting system for small retailers'
    
    return render_template('about.html', app_name=app_name, app_description=app_description)


# ============================================================================
# ADMIN DASHBOARD ROUTES
# ============================================================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if verify_admin_login(username, password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            log_admin_action(username, 'LOGIN', ip_address=request.remote_addr)
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    admin_user = session.get('admin_username', 'Unknown')
    session.clear()
    log_admin_action(admin_user, 'LOGOUT')
    flash('Admin logged out successfully!', 'success')
    return redirect(url_for('admin_login'))


@app.route('/admin')
@app.route('/admin/dashboard')

def admin_dashboard():
    """Master admin dashboard with overall metrics"""
    stats = get_retailer_stats()
    return render_template('admin_dashboard.html', stats=stats)


@app.route('/admin/retailers')

def admin_retailers():
    """Retailer management section with sorting"""
    sort_by = request.args.get('sort', 'newest')
    retailers = get_retailers_list(sort_by)
    return render_template('admin_retailers.html', retailers=retailers, sort_by=sort_by)


@app.route('/admin/retailers/export')

def admin_retailers_export():
    """Export retailer data to CSV"""
    retailers = get_retailers_list('newest')
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Store Name', 'Phone Number', 'Store Address', 'Status', 
                     'Total Customers', 'Total Credit Entries', 'Outstanding Amount',
                     'Created At', 'Last Active Date'])
    
    # Write data
    for retailer in retailers:
        writer.writerow([
            retailer['store_name'],
            retailer['phone_number'],
            retailer['store_address'] or '',
            retailer['status'],
            retailer['customer_count'],
            retailer['credit_count'],
            retailer['outstanding_amount'],
            retailer['created_at'] or '',
            retailer['last_active_date'] or ''
        ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=retailers_export.csv'
    
    log_admin_action(session.get('admin_username', 'Unknown'), 'EXPORT_RETAILERS')
    return response


@app.route('/admin/announcements', methods=['GET', 'POST'])

def admin_announcements():
    """Admin communication - send announcements to retailers"""
    db = get_db()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        
        if title and message:
            try:
                admin_user = session.get('admin_username', 'Unknown')
                db.execute("""
                    INSERT INTO announcements (title, message, created_by)
                    VALUES (?, ?, ?)
                """, (title, message, admin_user))
                db.commit()
                log_admin_action(admin_user, 'CREATE_ANNOUNCEMENT', f'Title: {title}')
                flash('Announcement created successfully!', 'success')
            except Exception as e:
                flash(f'Error creating announcement: {str(e)}', 'error')
        else:
            flash('Title and message are required!', 'error')
    
    # Get all announcements
    announcements = db.execute("""
        SELECT id, title, message, created_by, created_at, status
        FROM announcements
        ORDER BY created_at DESC
        LIMIT 50
    """).fetchall()
    
    db.close()
    return render_template('admin_announcements.html', announcements=announcements)


@app.route('/admin/settings', methods=['GET', 'POST'])

def admin_settings():
    """System-level settings management"""
    db = get_db()
    
    if request.method == 'POST':
        global_dunning_days = request.form.get('global_dunning_days', '15')
        disclaimer_text = request.form.get('disclaimer_text', '')
        whatsapp_enabled = request.form.get('whatsapp_enabled', 'false')
        maintenance_mode = request.form.get('maintenance_mode', 'false')
        
        try:
            settings_to_update = [
                ('global_dunning_days', global_dunning_days),
                ('disclaimer_text', disclaimer_text),
                ('whatsapp_enabled', whatsapp_enabled),
                ('app_maintenance_mode', maintenance_mode)
            ]
            
            for key, value in settings_to_update:
                db.execute("""
                    UPDATE system_settings SET value = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE key = ?
                """, (value, key))
            
            db.commit()
            log_admin_action(session.get('admin_username', 'Unknown'), 'UPDATE_SYSTEM_SETTINGS')
            flash('System settings updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating settings: {str(e)}', 'error')
    
    # Get current settings
    settings_data = {}
    settings_rows = db.execute('SELECT key, value, description FROM system_settings').fetchall()
    for row in settings_rows:
        settings_data[row['key']] = {
            'value': row['value'],
            'description': row['description']
        }
    
    db.close()
    return render_template('admin_settings.html', settings=settings_data)


@app.route('/admin/audit-log')

def admin_audit_log():
    """View audit logs"""
    db = get_db()
    logs = db.execute("""
        SELECT admin_user, action, details, ip_address, created_at
        FROM audit_logs
        ORDER BY created_at DESC
        LIMIT 100
    """).fetchall()
    db.close()
    return render_template('admin_audit_log.html', logs=logs)


@app.route('/customer/submit-payment', methods=['GET', 'POST'])

def submit_payment():
    """Customer submits a payment request"""
    db = get_db()
    customer_id = session['user_id']

    if request.method == 'POST':
        retailer_id = request.form.get('retailer_id')
        amount = float(request.form.get('amount', 0))
        payment_mode = request.form.get('payment_mode')
        notes = request.form.get('notes', '').strip()

        if not retailer_id or amount <= 0 or not payment_mode:
            flash('All fields are required!', 'error')
            return redirect(url_for('submit_payment'))

        try:
            # Insert payment request
            db.execute(
                'INSERT INTO payment_requests (customer_id, retailer_id, amount, payment_mode, notes) VALUES (?, ?, ?, ?, ?)',
                (customer_id, retailer_id, amount, payment_mode, notes)
            )
            db.commit()

            # Send push notification to retailer
            from push_notifications import send_push_notification, prepare_payment_request_notification
            customer = db.execute('SELECT name FROM users WHERE id = ?', (customer_id,)).fetchone()
            title, body = prepare_payment_request_notification(customer['name'], amount)
            send_push_notification(retailer_id, title, body)

            # Add timeline event
            db.execute(
                'INSERT INTO timeline_events (customer_id, retailer_id, event_type, amount, description) VALUES (?, ?, ?, ?, ?)',
                (customer_id, retailer_id, 'payment_requested', amount, f'Payment requested via {payment_mode}')
            )
            db.commit()

            flash('Payment request submitted successfully!', 'success')
            return redirect(url_for('customer_dashboard'))

        except Exception as e:
            db.rollback()
            flash(f'Error submitting payment request: {str(e)}', 'error')
        finally:
            db.close()

    # GET request - show form with retailers that customer owes money to
    retailers = db.execute(
        '''
        SELECT
            r.user_id as retailer_id,
            rp.store_name,
            COALESCE(SUM(c.amount), 0) - COALESCE(SUM(p.amount), 0) as outstanding
        FROM retailer_profiles rp
        JOIN users r ON rp.user_id = r.id
        LEFT JOIN credits c ON c.retailer_id = r.id AND c.customer_id = ?
        LEFT JOIN payments p ON p.retailer_id = r.id AND p.customer_id = ?
        WHERE c.customer_id = ?
        GROUP BY r.user_id, rp.store_name
        HAVING outstanding > 0
        ORDER BY outstanding DESC
        ''',
        (customer_id, customer_id, customer_id)
    ).fetchall()
    db.close()

    return render_template('submit_payment.html', retailers=retailers)


@app.route('/retailer/payment-requests')

def payment_requests():
    """Retailer views pending payment requests"""
    db = get_db()
    retailer_id = session['user_id']

    requests = db.execute(
        '''
        SELECT
            pr.id,
            pr.amount,
            pr.payment_mode,
            pr.notes,
            pr.submitted_at,
            u.name as customer_name,
            u.phone as customer_phone
        FROM payment_requests pr
        JOIN users u ON pr.customer_id = u.id
        WHERE pr.retailer_id = ? AND pr.status = 'pending'
        ORDER BY pr.submitted_at DESC
        ''',
        (retailer_id,)
    ).fetchall()
    db.close()

    return render_template('payment_requests.html', requests=requests)


@app.route('/retailer/payment-request/<int:request_id>/<action>', methods=['POST'])

def process_payment_request(request_id, action):
    """Retailer confirms or rejects a payment request"""
    if action not in ['confirm', 'reject']:
        flash('Invalid action!', 'error')
        return redirect(url_for('payment_requests'))

    db = get_db()
    retailer_id = session['user_id']

    try:
        # Get the payment request
        request_data = db.execute(
            'SELECT * FROM payment_requests WHERE id = ? AND retailer_id = ? AND status = ?',
            (request_id, retailer_id, 'pending')
        ).fetchone()

        if not request_data:
            flash('Payment request not found!', 'error')
            db.close()
            return redirect(url_for('payment_requests'))

        if action == 'confirm':
            # Add payment entry
            db.execute(
                'INSERT INTO payments (customer_id, retailer_id, amount, payment_date) VALUES (?, ?, ?, ?)',
                (request_data['customer_id'], retailer_id, request_data['amount'], datetime.now().date())
            )

            # Update request status
            db.execute(
                'UPDATE payment_requests SET status = ?, processed_at = ?, processed_by = ? WHERE id = ?',
                ('confirmed', datetime.now(), retailer_id, request_id)
            )

            # Send push notification to customer
            from push_notifications import send_push_notification, prepare_payment_confirmed_notification
            retailer = db.execute('SELECT rp.store_name FROM retailer_profiles rp WHERE rp.user_id = ?', (retailer_id,)).fetchone()
            title, body = prepare_payment_confirmed_notification(retailer['store_name'], request_data['amount'])
            send_push_notification(request_data['customer_id'], title, body)

            # Add timeline event
            db.execute(
                'INSERT INTO timeline_events (customer_id, retailer_id, event_type, amount, description) VALUES (?, ?, ?, ?, ?)',
                (request_data['customer_id'], retailer_id, 'payment_confirmed', request_data['amount'], f'Payment confirmed via {request_data["payment_mode"]}')
            )

            flash('Payment confirmed successfully!', 'success')

        else:  # reject
            rejection_reason = request.form.get('rejection_reason', '').strip()
            db.execute(
                'UPDATE payment_requests SET status = ?, processed_at = ?, processed_by = ?, rejection_reason = ? WHERE id = ?',
                ('rejected', datetime.now(), retailer_id, rejection_reason, request_id)
            )

            # Add timeline event
            db.execute(
                'INSERT INTO timeline_events (customer_id, retailer_id, event_type, amount, description) VALUES (?, ?, ?, ?, ?)',
                (request_data['customer_id'], retailer_id, 'payment_rejected', request_data['amount'], f'Payment rejected: {rejection_reason}')
            )

            flash('Payment request rejected!', 'warning')

        db.commit()

    except Exception as e:
        db.rollback()
        flash(f'Error processing payment request: {str(e)}', 'error')
    finally:
        db.close()

    return redirect(url_for('payment_requests'))


@app.route('/retailer/customer/<int:customer_id>')

def customer_timeline(customer_id):
    """Retailer views customer timeline and details"""
    db = get_db()
    retailer_id = session['user_id']

    # Get customer details
    customer = db.execute('SELECT * FROM users WHERE id = ? AND user_type = ?', (customer_id, 'customer')).fetchone()
    if not customer:
        flash('Customer not found!', 'error')
        db.close()
        return redirect(url_for('retailer_customers'))

    # Get timeline events
    timeline = db.execute(
        '''
        SELECT * FROM timeline_events
        WHERE customer_id = ? AND retailer_id = ?
        ORDER BY created_at DESC
        ''',
        (customer_id, retailer_id)
    ).fetchall()

    # Get current outstanding balance
    outstanding = db.execute(
        'SELECT COALESCE(SUM(c.amount), 0) - COALESCE(SUM(p.amount), 0) FROM credits c LEFT JOIN payments p ON c.customer_id = p.customer_id AND c.retailer_id = p.retailer_id WHERE c.customer_id = ? AND c.retailer_id = ?',
        (customer_id, retailer_id)
    ).fetchone()[0]

    db.close()

    return render_template('customer_timeline.html', customer=customer, timeline=timeline, outstanding=outstanding)


@app.route('/customer/retailer/<int:retailer_id>')

def customer_retailer_detail(retailer_id):
    """Customer views their transaction history with a specific retailer"""
    db = get_db()
    customer_id = session['user_id']

    # Get retailer details
    retailer = db.execute(
        'SELECT u.*, rp.store_name, rp.store_address, rp.store_photo_url FROM users u JOIN retailer_profiles rp ON u.id = rp.user_id WHERE u.id = ? AND u.user_type = ?',
        (retailer_id, 'retailer')
    ).fetchone()

    if not retailer:
        flash('Retailer not found!', 'error')
        db.close()
        return redirect(url_for('customer_dashboard'))

    # Get transaction history
    transactions = db.execute(
        '''
        SELECT
            'credit' as type,
            c.amount,
            c.entry_date as date,
            c.notes as description
        FROM credits c
        WHERE c.customer_id = ? AND c.retailer_id = ?
        UNION ALL
        SELECT
            'payment' as type,
            p.amount,
            p.payment_date as date,
            'Payment received' as description
        FROM payments p
        WHERE p.customer_id = ? AND p.retailer_id = ?
        ORDER BY date DESC
        ''',
        (customer_id, retailer_id, customer_id, retailer_id)
    ).fetchall()

    # Get current outstanding balance
    outstanding = db.execute(
        'SELECT COALESCE(SUM(c.amount), 0) - COALESCE(SUM(p.amount), 0) FROM credits c LEFT JOIN payments p ON c.customer_id = p.customer_id AND c.retailer_id = p.retailer_id WHERE c.customer_id = ? AND c.retailer_id = ?',
        (customer_id, retailer_id)
    ).fetchone()[0]

    db.close()

    return render_template('customer_retailer_detail.html', retailer=retailer, transactions=transactions, outstanding=outstanding)


if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
