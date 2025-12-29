"""
Retail App - Core Accounting Logic
A simple Flask application for managing customer credits and payments
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, make_response
from datetime import datetime, timedelta
from database import init_db, get_db
from whatsapp_helper import send_whatsapp_message, prepare_welcome_message, prepare_credit_confirmation_message, prepare_pre_due_reminder_message
from firebase_config import (
    get_user_store_data, save_user_store_data,
    is_user_logged_in, get_current_user_id, get_current_user_phone
)
from admin_helper import (
    verify_admin_login, log_admin_action, get_retailer_stats, 
    get_retailers_list, sync_retailer_from_firebase
)
from admin_helper import (
    verify_admin_login, log_admin_action, get_retailer_stats, 
    get_retailers_list, sync_retailer_from_firebase
)
import sqlite3
from functools import wraps
import csv
import io
import csv
import io

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # Change this in production

# Initialize database on startup
init_db()


# ============================================================================
# AUTHENTICATION & AUTHORIZATION HELPERS
# ============================================================================

def require_login(f):
    """Decorator to require user login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_user_logged_in():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Decorator to require admin authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in', False):
            flash('Admin access required!', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Decorator to require admin authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in', False):
            flash('Admin access required!', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page with phone number OTP authentication
    On first login, redirects to onboarding. On subsequent logins, redirects to dashboard.
    """
    if request.method == 'POST':
        phone_number = request.form.get('phone_number', '').strip()
        verification_code = request.form.get('verification_code', '').strip()
        
        if not phone_number:
            flash('Phone number is required!', 'error')
            return render_template('login.html')
        
        # Clean phone number format
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        
        # For demo/simplified implementation:
        # In production, you'd integrate with Firebase Phone Auth properly
        # This is a simplified version - you'll need to implement actual Firebase Phone Auth flow
        
        # Simplified: For now, we'll use a basic authentication
        # Replace this with actual Firebase Phone Auth implementation
        if verification_code:
            # Verify OTP (simplified - implement proper Firebase Phone Auth)
            # For now, accept any 6-digit code for demo purposes
            if len(verification_code) == 6 and verification_code.isdigit():
                # In production: verify_phone_otp(phone_number, verification_code)
                # For demo: simulate successful login
                try:
                    # Set session (in production, get user_id from Firebase Auth)
                    session['phone_number'] = phone_number
                    session['user_id'] = phone_number.replace('+', '').replace(' ', '').replace('-', '')
                    
                    # Check if user exists (has store data)
                    user_id = session['user_id']
                    store_data = get_user_store_data(user_id)
                    
                    # Update retailer activity tracking
                    if store_data:
                        sync_retailer_from_firebase(
                            user_id, 
                            phone_number, 
                            store_data.get('store_name', ''),
                            store_data.get('store_address', '')
                        )
                    
                    if store_data:
                        # User exists - redirect to dashboard
                        flash('Login successful!', 'success')
                        return redirect(url_for('dashboard'))
                    else:
                        # New user - redirect to onboarding
                        return redirect(url_for('onboarding'))
                except Exception as e:
                    flash(f'Login error: {str(e)}', 'error')
            else:
                flash('Invalid verification code!', 'error')
        else:
            # Step 1: Send OTP (simplified - implement proper Firebase Phone Auth)
            # In production: auth.send_phone_verification_code(phone_number)
            flash(f'OTP sent to {phone_number}. Please check your phone.', 'success')
            return render_template('login.html', phone_number=phone_number, show_otp_input=True)
    
    return render_template('login.html')


@app.route('/onboarding', methods=['GET', 'POST'])
@require_login
def onboarding():
    """
    Onboarding page for first-time users to enter store details
    Only accessible if user is logged in but doesn't have store data
    """
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


@app.route('/logout')
def logout():
    """Logout user and clear session"""
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))


# ============================================================================
# DASHBOARD - Main landing page with 4 cards
# ============================================================================

@app.route('/')
@app.route('/dashboard')
@require_login
def dashboard():
    """Dashboard page - shows 4 main navigation cards (requires login)"""
    return render_template('dashboard.html')


# ============================================================================
# CUSTOMER MASTER OPERATIONS
# ============================================================================

@app.route('/customers')
def index():
    """Customer list page - shows list of customers"""
    db = get_db()
    customers = db.execute(
        'SELECT id, name, phone, address FROM customers ORDER BY name'
    ).fetchall()
    db.close()
    return render_template('index.html', customers=customers)


@app.route('/customer/add', methods=['GET', 'POST'])
@require_login
def add_customer():
    """Add a new customer to the master"""
    if request.method == 'POST':
        # Debug: Print form data
        print(f"DEBUG: Form data received: {dict(request.form)}")
        
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        debit_amount = request.form.get('debit_amount', '').strip()
        due_days = request.form.get('due_days', '30').strip()
        
        print(f"DEBUG: Processed data - name: '{name}', phone: '{phone}', address: '{address}', debit_amount: '{debit_amount}', due_days: '{due_days}'")
        
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
                due_days_int = int(due_days) if due_days else 30

                # Validate due_days - must be one of the allowed options
                allowed_due_days = [7, 10, 14, 21, 25, 30, 45, 60]
                if due_days_int not in allowed_due_days:
                    db.close()
                    flash('Please select a valid due days option!', 'error')
                    return render_template('add_customer.html')

                # Calculate due date automatically
                entry_date = datetime.now().date()
                due_date = entry_date + timedelta(days=due_days_int)

                db.execute(
                    'INSERT INTO credits (customer_id, amount, entry_date, due_days, due_date) VALUES (?, ?, ?, ?, ?)',
                    (customer_id, amount, entry_date, due_days_int, due_date)
                )
                db.commit()
                
                # Create transaction record for the debit
                db.execute(
                    'INSERT INTO transactions (customer_id, type, amount, description) VALUES (?, ?, ?, ?)',
                    (customer_id, 'DEBIT', amount, f'Initial credit entry - Due in {due_days_int} days')
                )
                db.commit()
                
                print(f"DEBUG: Credit entry added for customer {customer_id}: amount={amount}, due_date={due_date}")
                
                # Send immediate credit confirmation message for initial debit
                if phone:
                    try:
                        # Get store name from settings
                        store_setting = db.execute(
                            "SELECT value FROM settings WHERE key = 'store_name'"
                        ).fetchone()
                        store_name = store_setting['value'] if store_setting and store_setting['value'] else 'Your Store'
                        
                        # Prepare and send credit confirmation message
                        confirmation_msg = prepare_credit_confirmation_message(
                            name,
                            store_name,
                            amount,
                            due_date
                        )
                        send_whatsapp_message(phone, confirmation_msg)
                    except Exception as e:
                        # Don't fail customer creation if WhatsApp fails
                        print(f"Warning: Could not send initial credit confirmation WhatsApp: {str(e)}")
            
            # Send welcome WhatsApp message if phone number is provided
            if phone:
                try:
                    # Get store name from settings
                    store_setting = db.execute(
                        "SELECT value FROM settings WHERE key = 'store_name'"
                    ).fetchone()
                    store_name = store_setting['value'] if store_setting and store_setting['value'] else 'Your Store'
                    
                    # Prepare and send welcome message
                    welcome_msg = prepare_welcome_message(name, store_name)
                    send_whatsapp_message(phone, welcome_msg)
                except Exception as e:
                    # Don't fail customer creation if WhatsApp fails
                    print(f"Warning: Could not send welcome WhatsApp: {str(e)}")
            
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
@require_login
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
@require_login
def add_credit(customer_id=None):
    """Add a credit entry with auto-calculated due date (requires login)"""
    db = get_db()
    
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        amount = float(request.form['amount'])
        due_days = int(request.form['due_days'])
        
        # Validate due_days - must be one of the allowed options
        allowed_due_days = [7, 10, 14, 21, 25, 30, 45, 60]
        if due_days not in allowed_due_days:
            flash('Please select a valid due days option!', 'error')
            customers = db.execute('SELECT id, name FROM customers ORDER BY name').fetchall()
            selected_customer_obj = None
            if 'customer_id' in request.form and request.form['customer_id']:
                selected_customer_obj = db.execute(
                    'SELECT id, name FROM customers WHERE id = ?',
                    (request.form['customer_id'],)
                ).fetchone()
            db.close()
            return render_template('add_credit.html', customers=customers, selected_customer=selected_customer_obj)
        
        # Calculate due date automatically
        entry_date = datetime.now().date()
        due_date = entry_date + timedelta(days=due_days)
        
        # Calculate reminder date (days before due date)
        reminder_days_before = int(db.execute(
            "SELECT value FROM settings WHERE key = 'reminder_days_before_due'"
        ).fetchone()['value'])
        reminder_date = due_date - timedelta(days=reminder_days_before)
        
        # Prepare WhatsApp reminder message
        customer = db.execute(
            'SELECT name, phone FROM customers WHERE id = ?',
            (customer_id,)
        ).fetchone()
        
        store_setting = db.execute(
            "SELECT value FROM settings WHERE key = 'store_name'"
        ).fetchone()
        store_name = store_setting['value'] if store_setting and store_setting['value'] else 'Your Store'
        
        # Calculate outstanding balance for the message
        total_credits = db.execute(
            'SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND type = ?',
            (customer_id, 'DEBIT')
        ).fetchone()[0]
        total_payments = db.execute(
            'SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND type = ?',
            (customer_id, 'PAYMENT')
        ).fetchone()[0]
        outstanding_balance = total_credits - total_payments
        
        whatsapp_message = prepare_pre_due_reminder_message(
            customer['name'],
            store_name,
            outstanding_balance,
            due_date,
            reminder_days_before
        )
        
        try:
            db.execute(
                'INSERT INTO credits (customer_id, amount, entry_date, due_days, due_date, reminder_date, whatsapp_message) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (customer_id, amount, entry_date, due_days, due_date, reminder_date, whatsapp_message)
            )
            db.commit()
            
            # Create transaction record for the debit
            db.execute(
                'INSERT INTO transactions (customer_id, type, amount, description) VALUES (?, ?, ?, ?)',
                (customer_id, 'DEBIT', amount, f'Credit entry - Due in {due_days} days')
            )
            db.commit()
            
            # Send immediate credit confirmation message
            try:
                # Get customer details
                customer = db.execute(
                    'SELECT name, phone FROM customers WHERE id = ?',
                    (customer_id,)
                ).fetchone()
                
                if customer and customer['phone']:
                    # Get store name from settings
                    store_setting = db.execute(
                        "SELECT value FROM settings WHERE key = 'store_name'"
                    ).fetchone()
                    store_name = store_setting['value'] if store_setting and store_setting['value'] else 'Your Store'
                    
                    # Prepare and send credit confirmation message
                    confirmation_msg = prepare_credit_confirmation_message(
                        customer['name'],
                        store_name,
                        amount,
                        due_date
                    )
                    send_whatsapp_message(customer['phone'], confirmation_msg)
            except Exception as e:
                # Don't fail credit entry if WhatsApp fails
                print(f"Warning: Could not send credit confirmation WhatsApp: {str(e)}")
            
            # Check if due date is today or has passed, and send reminder if needed
            # This will send reminder immediately if due date equals today or is in the past
            today = datetime.now().date()
            if due_date <= today:
                try:
                    # Get customer details
                    customer = db.execute(
                        'SELECT name, phone FROM customers WHERE id = ?',
                        (customer_id,)
                    ).fetchone()
                    
                    if customer and customer['phone']:
                        # Calculate outstanding balance
                        total_debits = db.execute(
                            'SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND type = ?',
                            (customer_id, 'DEBIT')
                        ).fetchone()[0]
                        total_payments = db.execute(
                            'SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND type = ?',
                            (customer_id, 'PAYMENT')
                        ).fetchone()[0]
                        outstanding_balance = total_debits - total_payments
                        
                        # Only send if balance > 0
                        if outstanding_balance > 0:
                            # Get store name from settings
                            store_setting = db.execute(
                                "SELECT value FROM settings WHERE key = 'store_name'"
                            ).fetchone()
                            store_name = store_setting['value'] if store_setting and store_setting['value'] else 'Your Store'
                            
                            # Calculate days overdue (0 if due today, >0 if past due)
                            days_overdue = (today - due_date).days
                            
                            # Prepare and send reminder message with days overdue
                            reminder_msg = prepare_reminder_message(
                                customer['name'],
                                store_name,
                                outstanding_balance,
                                due_date,
                                days_overdue
                            )
                            send_whatsapp_message(customer['phone'], reminder_msg)
                except Exception as e:
                    # Don't fail credit entry if WhatsApp fails
                    print(f"Warning: Could not send reminder WhatsApp: {str(e)}")
            
            flash(f'Credit entry added successfully! Due date: {due_date}', 'success')
            # Instead of redirecting, show success page with action buttons
            customer = db.execute(
                'SELECT id, name FROM customers WHERE id = ?',
                (customer_id,)
            ).fetchone()
            db.close()
            return render_template('credit_success.html', customer=customer, amount=amount, due_date=due_date)
        except Exception as e:
            db.close()
            flash(f'Error adding credit entry: {str(e)}', 'error')
    
    # GET request - show form
    customers = db.execute('SELECT id, name FROM customers ORDER BY name').fetchall()
    selected_customer = None
    if customer_id:
        selected_customer = db.execute(
            'SELECT id, name FROM customers WHERE id = ?',
            (customer_id,)
        ).fetchone()

    db.close()
    return render_template('add_credit.html', customers=customers, selected_customer=selected_customer)


# ============================================================================
# PAYMENT ENTRY OPERATIONS
# ============================================================================

@app.route('/payment/add', methods=['GET', 'POST'])
@app.route('/payment/add/<int:customer_id>', methods=['GET', 'POST'])
@require_login
def add_payment(customer_id=None):
    """Add a payment entry that reduces outstanding balance (requires login)"""
    db = get_db()
    
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        amount = float(request.form['amount'])
        
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
            flash(f'Error adding payment: {str(e)}', 'error')
    
    # GET request - show form
    customers = db.execute('SELECT id, name FROM customers ORDER BY name').fetchall()
    selected_customer = None
    if customer_id:
        selected_customer = db.execute(
            'SELECT id, name FROM customers WHERE id = ?',
            (customer_id,)
        ).fetchone()

    return render_template('add_payment.html', customers=customers, selected_customer=selected_customer)


# ============================================================================
# OVERDUE DETECTION
# ============================================================================

@app.route('/overdue')
@require_login
def overdue_list():
    """
    Show all overdue entries where balance > 0 and due_date < today
    Note: This shows credits with due dates passed, checking if customer has outstanding balance
    """
    db = get_db()
    today = datetime.now().date()
    
    # Get all overdue credits and check if customer has outstanding balance
    # For simplicity, we show credits where due_date < today and customer has outstanding balance
    overdue_items = db.execute("""
        SELECT 
            c.id as credit_id,
            c.customer_id,
            cust.name as customer_name,
            c.amount,
            c.entry_date,
            c.due_date,
            c.due_days,
            (SELECT COALESCE(SUM(amount), 0) 
             FROM transactions WHERE customer_id = c.customer_id AND type = 'DEBIT') as total_debits,
            (SELECT COALESCE(SUM(amount), 0) 
             FROM transactions WHERE customer_id = c.customer_id AND type = 'PAYMENT') as total_payments
        FROM credits c
        JOIN customers cust ON c.customer_id = cust.id
        WHERE c.due_date < ?
        ORDER BY c.due_date ASC
    """, (today,)).fetchall()
    
    # Calculate outstanding balance and filter
    overdue_with_balance = []
    for item in overdue_items:
        outstanding_balance = item['total_debits'] - item['total_payments']
        if outstanding_balance > 0:
            # Parse due_date string to date object for calculation
            due_date = datetime.strptime(item['due_date'], '%Y-%m-%d').date() if isinstance(item['due_date'], str) else item['due_date']
            days_overdue = (today - due_date).days
            
            overdue_with_balance.append({
                'credit_id': item['credit_id'],
                'customer_id': item['customer_id'],
                'customer_name': item['customer_name'],
                'amount': item['amount'],
                'entry_date': item['entry_date'],
                'due_date': item['due_date'],  # Keep as string for display
                'due_days': item['due_days'],
                'total_payments': item['total_payments'],
                'outstanding_balance': outstanding_balance,
                'days_overdue': days_overdue
            })
    
    return render_template('overdue.html', overdue_items=overdue_with_balance, today=today)


# ============================================================================
# AGEING REPORT
# ============================================================================

@app.route('/ageing')
@require_login
def ageing_report():
    """
    Generate ageing report with custom buckets: 0-7, 8-10, 11-15, 16-20, 21-25, 26-30, 31-45 days
    Only shows overdue credits (due_date < today) where customer has outstanding balance > 0
    """
    db = get_db()
    today = datetime.now().date()
    
    # Get customer outstanding balances (to filter only credits where balance > 0)
    customer_balances = {}
    balance_data = db.execute("""
        SELECT 
            id as customer_id,
            (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = customers.id AND type = 'DEBIT') as total_debits,
            (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = customers.id AND type = 'PAYMENT') as total_payments
        FROM customers
    """).fetchall()
    
    for row in balance_data:
        balance = row['total_debits'] - row['total_payments']
        if balance > 0:
            customer_balances[row['customer_id']] = balance
    
    # Get all overdue credits (due_date < today) for customers with outstanding balance
    # Calculate days overdue and assign to custom buckets
    overdue_credits = db.execute("""
        SELECT 
            cust.id as customer_id,
            cust.name as customer_name,
            c.id as credit_id,
            c.amount as balance,
            c.due_date,
            (julianday(?) - julianday(c.due_date)) as days_overdue
        FROM credits c
        JOIN customers cust ON c.customer_id = cust.id
        WHERE c.due_date < ?
        ORDER BY cust.name, c.due_date
    """, (today, today)).fetchall()
    
    # Build report data: assign each overdue credit to a bucket
    report_data = []
    for credit in overdue_credits:
        customer_id = credit['customer_id']
        # Only include if customer has outstanding balance
        if customer_id in customer_balances:
            days_overdue = int(credit['days_overdue'])
            
            # Assign to custom bucket based on days overdue
            if days_overdue <= 7:
                bucket = '0-7 days'
            elif days_overdue <= 10:
                bucket = '8-10 days'
            elif days_overdue <= 15:
                bucket = '11-15 days'
            elif days_overdue <= 20:
                bucket = '16-20 days'
            elif days_overdue <= 25:
                bucket = '21-25 days'
            elif days_overdue <= 30:
                bucket = '26-30 days'
            elif days_overdue <= 45:
                bucket = '31-45 days'
            else:
                bucket = 'Over 45 days'  # Handle edge case
            
            report_data.append({
                'customer_name': credit['customer_name'],
                'balance': credit['balance'],
                'days_overdue': days_overdue,
                'bucket': bucket,
                'due_date': credit['due_date']
            })
    
    return render_template('ageing.html', report_data=report_data, today=today)


# ============================================================================
# CUSTOMER LEDGER
# ============================================================================

@app.route('/ledger/<int:customer_id>')
@require_login
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
        SELECT id, amount, entry_date, due_date, due_days
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
@require_login
def debtor_details():
    """
    Show all customers with outstanding balance > 0.
    Shows one row per customer with their total outstanding balance,
    next due date, and days until due (can be negative for overdue).
    """
    db = get_db()
    today = datetime.now().date()
    
    # Get sort option from query parameter (default: due date ascending)
    sort_option = request.args.get('sort', 'due_asc')
    
    # Get all customers with outstanding balance > 0
    debtor_data = db.execute("""
        SELECT
            cust.id as customer_id,
            cust.name as customer_name,
            cust.phone,
            (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = cust.id AND type = 'DEBIT') as total_debits,
            (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = cust.id AND type = 'PAYMENT') as total_payments,
            (SELECT MIN(due_date) FROM credits WHERE customer_id = cust.id AND due_date >= ?) as next_due_date,
            (SELECT COUNT(*) FROM credits WHERE customer_id = cust.id AND due_date < ?) as overdue_count
        FROM customers cust
        WHERE (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = cust.id AND type = 'DEBIT') -
              (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = cust.id AND type = 'PAYMENT') > 0
        ORDER BY cust.name
    """, (today, today)).fetchall()
    
    # Build debtor list
    debtor_list = []
    for row in debtor_data:
        outstanding_balance = max(0, row['total_debits'] - row['total_payments'])  # Ensure no negative
        
        # Get next due date (earliest future due date, or earliest past due date if no future)
        next_due_date = row['next_due_date']
        if not next_due_date:
            # If no future due dates, get the most recent past due date
            past_due = db.execute("""
                SELECT MAX(due_date) FROM credits 
                WHERE customer_id = ? AND due_date < ?
            """, (row['customer_id'], today)).fetchone()[0]
            next_due_date = past_due
        
        if next_due_date:
            # Calculate days until due (can be negative for overdue)
            if isinstance(next_due_date, str):
                due_date_obj = datetime.strptime(next_due_date, '%Y-%m-%d').date()
            else:
                due_date_obj = next_due_date
            
            days_until_due = (due_date_obj - today).days
            
            # Determine status and bucket
            if days_until_due < 0:
                status = 'overdue'
                days_overdue = abs(days_until_due)
                # Ageing bucket for overdue
                if days_overdue <= 7:
                    bucket = '0-7 days'
                elif days_overdue <= 10:
                    bucket = '8-10 days'
                elif days_overdue <= 15:
                    bucket = '11-15 days'
                elif days_overdue <= 20:
                    bucket = '16-20 days'
                elif days_overdue <= 25:
                    bucket = '21-25 days'
                elif days_overdue <= 30:
                    bucket = '26-30 days'
                elif days_overdue <= 45:
                    bucket = '31-45 days'
                else:
                    bucket = 'Over 45 days'
            else:
                status = 'current'
                days_overdue = 0
                # Bucket for current accounts
                if days_until_due <= 7:
                    bucket = 'Due within 7 days'
                elif days_until_due <= 14:
                    bucket = 'Due within 14 days'
                elif days_until_due <= 30:
                    bucket = 'Due within 30 days'
                else:
                    bucket = 'Due in 30+ days'
            
            debtor_list.append({
                'customer_id': row['customer_id'],
                'customer_name': row['customer_name'],
                'phone': row['phone'],
                'outstanding_balance': outstanding_balance,
                'due_date': next_due_date,
                'days_until_due': days_until_due,
                'days_overdue': days_overdue,
                'status': status,
                'bucket': bucket,
                'overdue_count': row['overdue_count']
            })
    
    # Apply sorting
    if sort_option == 'due_asc':
        debtor_list.sort(key=lambda x: x['days_until_due'])
    elif sort_option == 'due_desc':
        debtor_list.sort(key=lambda x: x['days_until_due'], reverse=True)
    elif sort_option == 'balance_desc':
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
        print(f"  {debtor['customer_name']}: {debtor['outstanding_balance']:.2f}, due: {debtor['due_date']}, days: {debtor['days_until_due']}")
    
    db.close()
    return render_template('debtor_details.html', 
                         debtor_list=debtor_list, 
                         sort_option=sort_option, 
                         today=today)


# ============================================================================
# SETTINGS - Admin configuration page
# ============================================================================

@app.route('/settings', methods=['GET', 'POST'])
@require_login
def settings():
    """
    Settings page for store profile and basic configuration
    """
    db = get_db()
    
    if request.method == 'POST':
        # Update only store and configuration settings
        default_dunning_days = request.form.get('default_dunning_days', '15')
        store_name = request.form.get('store_name', 'Your Store')
        store_address = request.form.get('store_address', '')
        store_email = request.form.get('store_email', '')
        
        # Update settings
        settings_to_update = [
            ('default_dunning_days', default_dunning_days),
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
    
    # Get current settings
    settings_data = {}
    settings_rows = db.execute('SELECT key, value, description FROM settings').fetchall()
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
# ABOUT APP - Static information page
# ============================================================================

@app.route('/about')
@require_login
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
@require_admin
def admin_dashboard():
    """Master admin dashboard with overall metrics"""
    stats = get_retailer_stats()
    return render_template('admin_dashboard.html', stats=stats)


@app.route('/admin/reminders')
@require_admin
def admin_reminders():
    """Show pending payment reminders that need to be sent"""
    db = get_db()
    today = datetime.now().date()
    
    # Get all credits where reminder_date is today or in the past, and customer has outstanding balance
    reminders = db.execute("""
        SELECT 
            c.id as credit_id,
            c.customer_id,
            cust.name as customer_name,
            cust.phone,
            c.amount as credit_amount,
            c.due_date,
            c.reminder_date,
            c.whatsapp_message,
            (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.customer_id AND type = 'DEBIT') as total_debits,
            (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.customer_id AND type = 'PAYMENT') as total_payments
        FROM credits c
        JOIN customers cust ON c.customer_id = cust.id
        WHERE c.reminder_date <= ?
        ORDER BY c.reminder_date ASC, cust.name ASC
    """, (today,)).fetchall()
    
    # Filter to only show reminders where customer still has outstanding balance
    pending_reminders = []
    for reminder in reminders:
        outstanding_balance = reminder['total_debits'] - reminder['total_payments']
        if outstanding_balance > 0:
            pending_reminders.append({
                'credit_id': reminder['credit_id'],
                'customer_id': reminder['customer_id'],
                'customer_name': reminder['customer_name'],
                'phone': reminder['phone'],
                'outstanding_balance': outstanding_balance,
                'due_date': reminder['due_date'],
                'reminder_date': reminder['reminder_date'],
                'whatsapp_message': reminder['whatsapp_message']
            })
    
    db.close()
    return render_template('admin_reminders.html', reminders=pending_reminders, today=today)


@app.route('/admin/retailers')
@require_admin
def admin_retailers():
    """Retailer management section with sorting"""
    sort_by = request.args.get('sort', 'newest')
    retailers = get_retailers_list(sort_by)
    return render_template('admin_retailers.html', retailers=retailers, sort_by=sort_by)


@app.route('/admin/retailers/export')
@require_admin
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
@require_admin
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
@require_admin
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
@require_admin
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


if __name__ == '__main__':
    app.run(debug=True)
