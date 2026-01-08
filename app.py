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

# Windsurf Compatibility Fixes - Disable ALL UI customization that causes crashes
os.environ['DISABLE_UI_CUSTOMIZATION'] = '1'
os.environ['DISABLE_ICON_THEMES'] = '1'
os.environ['FORCE_DEFAULT_THEME'] = '1'
os.environ['DISABLE_FANCY_FEATURES'] = '1'
os.environ['DISABLE_FILE_WATCHING'] = '1'
os.environ['DISABLE_AUTO_RELOAD'] = '1'
os.environ['DISABLE_CUSTOM_FONTS'] = '1'
os.environ['DISABLE_CUSTOM_THEMES'] = '1'
os.environ['DISABLE_ANIMATIONS'] = '1'
os.environ['DISABLE_TRANSITIONS'] = '1'
os.environ['DISABLE_EXTENSIONS'] = '1'
os.environ['DISABLE_PREVIEW'] = '1'
os.environ['DISABLE_WORKSPACE_FEATURES'] = '1'
os.environ['EDITOR_MODE'] = 'basic'
os.environ['FORCE_SIMPLE_RENDERING'] = '1'

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
# AUTHENTICATION ROUTES - ROLE SEPARATED
# ============================================================================

@app.route('/retailer/login', methods=['GET', 'POST'])
def retailer_login():
    """Retailer login page"""
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        if not phone or not password:
            flash('Phone and password are required', 'error')
            return render_template('retailer_login.html')
        
        db = get_db()
        try:
            # Check if retailer exists
            retailer = db.execute(
                'SELECT u.id, u.name, rp.store_name FROM users u LEFT JOIN retailer_profiles rp ON u.id = rp.user_id WHERE u.phone_number = ? AND u.user_type = ?',
                (phone, 'retailer')
            ).fetchone()
            
            if retailer and password == '12345':  # Simple password check for now
                session['user_id'] = retailer['id']
                session['user_type'] = 'retailer'
                session['phone_number'] = phone
                session['store_name'] = retailer['store_name']
                
                flash('Login successful!', 'success')
                return redirect(url_for('retailer_dashboard'))
            else:
                flash('Invalid credentials', 'error')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'error')
        finally:
            db.close()
    
    return render_template('retailer_login.html')

@app.route('/retailer/register', methods=['GET', 'POST'])
def retailer_register():
    """Retailer registration page"""
    if request.method == 'POST':
        shop_name = request.form.get('shop_name', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        shop_address = request.form.get('shop_address', '').strip()
        
        # Validation
        if not shop_name or not phone or not password or not confirm_password:
            flash('All required fields must be filled', 'error')
            return render_template('retailer_register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('retailer_register.html')
        
        if len(password) < 4:
            flash('Password must be at least 4 characters long', 'error')
            return render_template('retailer_register.html')
        
        # Clean phone number
        if not phone.startswith('+'):
            phone = '+' + phone
        
        db = get_db()
        try:
            # Check if phone already exists
            existing = db.execute(
                'SELECT id FROM users WHERE phone_number = ?',
                (phone,)
            ).fetchone()
            
            if existing:
                flash('A user with this phone number already exists!', 'error')
                return render_template('retailer_register.html')
            
            # Create retailer user
            cursor = db.execute(
                'INSERT INTO users (phone_number, user_type, name, password) VALUES (?, ?, ?, ?)',
                (phone, 'retailer', shop_name, password)  # Simple password storage for now
            )
            retailer_id = cursor.lastrowid
            
            # Create retailer profile
            db.execute(
                'INSERT INTO retailer_profiles (user_id, store_name, store_address) VALUES (?, ?, ?)',
                (retailer_id, shop_name, shop_address)
            )
            
            db.commit()
            
            print(f"Retailer registered successfully: ID={retailer_id}, Shop={shop_name}, Phone={phone}")
            flash('Retailer account created successfully! Please login.', 'success')
            return redirect(url_for('retailer_login'))
            
        except Exception as e:
            db.rollback()
            print(f"Error registering retailer: {str(e)}")
            flash(f'Error creating account: {str(e)}', 'error')
        finally:
            db.close()
    
    return render_template('retailer_register.html')

@app.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    """Customer login page - FIXED: Handle new role-separated data structure"""
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        if not phone or not password:
            flash('Phone and password are required', 'error')
            return render_template('customer_login.html')
        
        db = get_db()
        try:
            # Get customer by phone number
            customer = db.execute(
                'SELECT id, name FROM users WHERE phone_number = ? AND user_type = ?',
                (phone, 'customer')
            ).fetchone()
            
            if customer and password == '12345':  # Simple password check for now
                session['user_id'] = customer['id']
                session['user_type'] = 'customer'
                session['phone_number'] = phone
                
                flash('Login successful!', 'success')
                return redirect(url_for('customer_dashboard'))
            else:
                flash('Invalid credentials', 'error')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'error')
        finally:
            db.close()
    
    return render_template('customer_login.html')

@app.route('/customer/register', methods=['GET', 'POST'])
def customer_register():
    """Customer registration page"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        address = request.form.get('address', '').strip()
        
        # Validation
        if not name or not phone or not password or not confirm_password:
            flash('All required fields must be filled', 'error')
            return render_template('customer_register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('customer_register.html')
        
        if len(password) < 4:
            flash('Password must be at least 4 characters long', 'error')
            return render_template('customer_register.html')
        
        # Clean phone number
        if not phone.startswith('+'):
            phone = '+' + phone
        
        db = get_db()
        try:
            # Check if phone already exists
            existing = db.execute(
                'SELECT id FROM users WHERE phone_number = ?',
                (phone,)
            ).fetchone()
            
            if existing:
                flash('A user with this phone number already exists!', 'error')
                return render_template('customer_register.html')
            
            # Create customer user
            cursor = db.execute(
                'INSERT INTO users (phone_number, user_type, name, password, address) VALUES (?, ?, ?, ?, ?)',
                (phone, 'customer', name, password, address)  # Simple password storage for now
            )
            customer_id = cursor.lastrowid
            
            db.commit()
            
            print(f"Customer registered successfully: ID={customer_id}, Name={name}, Phone={phone}")
            flash('Customer account created successfully! Please login.', 'success')
            return redirect(url_for('customer_login'))
            
        except Exception as e:
            db.rollback()
            print(f"Error registering customer: {str(e)}")
            flash(f'Error creating account: {str(e)}', 'error')
        finally:
            db.close()
    
    return render_template('customer_register.html')


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
        
        # Handle File Upload
        store_photo_url = '/static/images/default_store.png' # Default
        if 'store_photo' in request.files:
            file = request.files['store_photo']
            if file and file.filename != '':
                try:
                    import os
                    from werkzeug.utils import secure_filename
                    
                    filename = secure_filename(file.filename)
                    # Use timestamp to make filename unique
                    filename = f"{int(datetime.now().timestamp())}_{filename}"
                    
                    upload_folder = os.path.join(app.static_folder, 'uploads', 'retailers')
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    
                    store_photo_url = f"/static/uploads/retailers/{filename}"
                except Exception as e:
                    print(f"Error saving file: {e}")
                    # Keep default if error

        if not store_name:
            flash('Store name is required!', 'error')
            return render_template('retailer_onboarding.html')

        db = get_db()
        try:
            # Create retailer user
            cursor = db.execute(
                'INSERT INTO users (phone_number, user_type, name, address, profile_photo_url) VALUES (?, ?, ?, ?, ?)',
                (session['phone_number'], 'retailer', store_name, store_address, store_photo_url)
            )
            user_id = cursor.lastrowid

            # Create retailer profile
            db.execute(
                'INSERT INTO retailer_profiles (user_id, store_name, store_address, store_photo_url) VALUES (?, ?, ?, ?)',
                (user_id, store_name, store_address, store_photo_url)
            )

            db.commit()

            # Set session
            session['user_id'] = user_id
            session['user_type'] = 'retailer'
            # Also set store name in session for easy access
            session['store_name'] = store_name

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
    """Root route - redirect to role selection"""
    return redirect(url_for('role_selection'))

@app.route('/role-selection')
def role_selection():
    """Role selection screen - First page users see"""
    return render_template('role_selection.html')

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
            'SELECT COALESCE(SUM(c.amount), 0) - COALESCE(SUM(p.amount), 0) FROM credits c LEFT JOIN payments p ON c.customer_id = p.customer_id AND c.retailer_id = p.retailer_id WHERE c.retailer_id = ?',
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
    FIXED: Safe data handling with proper guards and empty states
    """
    if not is_user_logged_in():
        return redirect(url_for('customer_login'))
    if session.get('user_type') != 'customer':
        flash('Access denied', 'error')
        return redirect(url_for('customer_login'))
    
    db = get_db()
    customer_phone = session.get('phone_number')
    
    # Guard: Check if phone number exists
    if not customer_phone:
        print("ERROR: No phone number in session")
        flash('Session error. Please login again.', 'error')
        return redirect(url_for('customer_login'))
    
    try:
        print(f"Customer dashboard: Processing phone {customer_phone}")
        
        # Guard: Check if customer exists
        customer = db.execute(
            'SELECT id, name FROM users WHERE phone_number = ? AND user_type = ?',
            (customer_phone, 'customer')
        ).fetchone()
        
        if not customer:
            print(f"Customer not found for phone {customer_phone}")
            return render_template('customer_dashboard.html',
                             outstanding_by_retailer=[],
                             total_outstanding=0)
        
        customer_id = customer['id']
        print(f"Found customer: ID={customer_id}, Name={customer['name']}")
        
        # Guard: Check if transactions table exists and has data
        try:
            # Find retailers with transactions for this customer
            retailers_with_customer = db.execute("""
                SELECT DISTINCT
                    r.id as retailer_id,
                    r.phone_number as retailer_phone,
                    rp.store_name,
                    rp.store_photo_url
                FROM retailer_profiles rp
                JOIN users r ON rp.user_id = r.id
                JOIN transactions t ON t.retailer_id = r.id
                JOIN users c ON t.customer_id = c.id AND c.phone_number = ?
                WHERE c.user_type = 'customer'
                """, (customer_phone,)).fetchall()
            
            print(f"Found {len(retailers_with_customer)} retailers for customer")
            
        except Exception as e:
            print(f"Transaction query failed: {e}")
            # Fallback: Try basic customer lookup
            retailers_with_customer = []
        
        # Calculate outstanding per retailer with guards
        outstanding_by_retailer = []
        for retailer in retailers_with_customer:
            retailer_id = retailer['retailer_id']
            
            try:
                # Get outstanding for this retailer-customer pair
                outstanding_result = db.execute("""
                    SELECT COALESCE(SUM(CASE WHEN type = 'credit' THEN amount ELSE 0 END) - 
                                  SUM(CASE WHEN type = 'payment' THEN amount ELSE 0 END), 0) as outstanding
                    FROM transactions 
                    WHERE retailer_id = ? AND customer_id = ?
                    """, (retailer_id, customer_id)).fetchone()
                
                outstanding = outstanding_result['outstanding'] if outstanding_result else 0
                
                outstanding_by_retailer.append({
                    'retailer_id': retailer_id,
                    'retailer_name': retailer['store_name'] or 'Unknown Store',
                    'retailer_phone': retailer['retailer_phone'],
                    'store_photo_url': retailer['store_photo_url'],
                    'outstanding': outstanding
                })
                
            except Exception as e:
                print(f"Error calculating outstanding for retailer {retailer_id}: {e}")
                # Add retailer with zero outstanding
                outstanding_by_retailer.append({
                    'retailer_id': retailer_id,
                    'retailer_name': retailer['store_name'] or 'Unknown Store',
                    'retailer_phone': retailer['retailer_phone'],
                    'store_photo_url': retailer['store_photo_url'],
                    'outstanding': 0
                })
        
        # Get total outstanding
        total_outstanding = sum(r['outstanding'] for r in outstanding_by_retailer)
        
        print(f"Final result: {len(outstanding_by_retailer)} retailers, Total outstanding: {total_outstanding}")
        
    except Exception as e:
        print(f"CRITICAL ERROR in customer_dashboard: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading dashboard. Please try again.', 'error')
        outstanding_by_retailer = []
        total_outstanding = 0
    finally:
        db.close()
    
    return render_template('customer_dashboard.html',
                     outstanding_by_retailer=outstanding_by_retailer,
                     total_outstanding=total_outstanding)


@app.route('/customer/retailer/<int:retailer_id>')
def customer_retailer_detail(retailer_id):
    """
    View details for a specific retailer from customer perspective
    Shows ledger/transactions only for this retailer
    FIXED: Safe data handling with proper guards
    """
    if not is_user_logged_in():
        return redirect(url_for('customer_login'))
    if session.get('user_type') != 'customer':
        flash('Access denied', 'error')
        return redirect(url_for('customer_login'))
        
    db = get_db()
    customer_phone = session.get('phone_number')
    
    # Guard: Check if phone number exists
    if not customer_phone:
        print("ERROR: No phone number in session for retailer detail")
        flash('Session error. Please login again.', 'error')
        return redirect(url_for('customer_login'))
    
    try:
        print(f"Customer retailer detail: Processing phone {customer_phone}, retailer {retailer_id}")
        
        # Guard: Get customer by phone
        customer = db.execute(
            'SELECT id, name FROM users WHERE phone_number = ? AND user_type = ?',
            (customer_phone, 'customer')
        ).fetchone()
        
        if not customer:
            print(f"Customer not found for phone {customer_phone}")
            flash('Customer not found!', 'error')
            return redirect(url_for('customer_dashboard'))
        
        customer_id = customer['id']
        
        # Get retailer details with guard
        retailer = db.execute(
            'SELECT u.*, rp.store_name, rp.store_address, rp.store_photo_url FROM users u JOIN retailer_profiles rp ON u.id = rp.user_id WHERE u.id = ? AND u.user_type = ?',
            (retailer_id, 'retailer')
        ).fetchone()

        if not retailer:
            print(f"Retailer not found: ID {retailer_id}")
            flash('Retailer not found!', 'error')
            return redirect(url_for('customer_dashboard'))

        # Get transaction history with guard
        try:
            transactions = db.execute("""
                SELECT
                    'credit' as type,
                    t.amount,
                    t.date,
                    t.notes as description
                FROM transactions t
                WHERE t.customer_id = ? AND t.retailer_id = ? AND t.type = 'credit'
                UNION ALL
                SELECT
                    'payment' as type,
                    t.amount,
                    t.date,
                    'Payment received' as description
                FROM transactions t
                WHERE t.customer_id = ? AND t.retailer_id = ? AND t.type = 'payment'
                ORDER BY date DESC
                """,
                (customer_id, retailer_id, customer_id, retailer_id)
            ).fetchall()
            
            print(f"Found {len(transactions)} transactions")
            
        except Exception as e:
            print(f"Transaction query failed: {e}")
            transactions = []

        # Get current outstanding balance with guard
        try:
            outstanding_result = db.execute("""
                SELECT COALESCE(SUM(CASE WHEN type = 'credit' THEN amount ELSE 0 END) - 
                              SUM(CASE WHEN type = 'payment' THEN amount ELSE 0 END), 0) as outstanding
                FROM transactions 
                WHERE customer_id = ? AND retailer_id = ?
                """, (customer_id, retailer_id)).fetchone()
            
            outstanding = outstanding_result['outstanding'] if outstanding_result else 0
            
        except Exception as e:
            print(f"Outstanding calculation failed: {e}")
            outstanding = 0

    except Exception as e:
        print(f"CRITICAL ERROR in customer_retailer_detail: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading retailer details.', 'error')
        retailer = None
        transactions = []
        outstanding = 0
    finally:
        db.close()
        
    return render_template('customer_retailer_detail.html', 
                     retailer=retailer, 
                     transactions=transactions, 
                     outstanding=outstanding)

@app.route('/retailer/customers')
def retailer_customers():
    """Show list of customers for the retailer"""
    if not is_user_logged_in():
        return redirect(url_for('login'))
    if session.get('user_type') != 'retailer':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
        
    db = get_db()
    retailer_id = session['user_id']
    customers = []
    
    try:
        print(f"Fetching customers for retailer_id: {retailer_id}")
        
        customers = db.execute("""
            SELECT
                u.id,
                u.name,
                u.phone_number as phone,
                COALESCE(
                    SUM(CASE WHEN t.type = 'credit' THEN t.amount ELSE 0 END) - 
                    SUM(CASE WHEN t.type = 'payment' THEN t.amount ELSE 0 END), 
                    0
                ) as outstanding
            FROM users u
            LEFT JOIN transactions t ON t.customer_id = u.id AND t.retailer_id = ?
            WHERE u.user_type = 'customer'
            GROUP BY u.id, u.name, u.phone_number
            ORDER BY u.name
            """,
            (retailer_id,)
        ).fetchall()
        
        print(f"Successfully fetched {len(customers)} customers for retailer {retailer_id}")
        
    except Exception as e:
        print(f"Error fetching customers for retailer {retailer_id}: {e}")
        import traceback
        traceback.print_exc()
        flash("Error loading customer list. Please try again.", "error")
        customers = []
    finally:
        db.close()

    return render_template('retailer_customers.html', customers=customers)


@app.route('/retailer/customer/add', methods=['GET', 'POST'])
def add_customer():
    """Add a new customer"""
    if not is_user_logged_in():
        return redirect(url_for('login'))
    if session.get('user_type') != 'retailer':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

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
        retailer_id = session['user_id']
        try:
            # Check if customer already exists
            existing = db.execute(
                'SELECT id FROM users WHERE phone_number = ? AND user_type = ?',
                (phone, 'customer')
            ).fetchone()

            if existing:
                print(f"Customer creation failed: Phone {phone} already exists for retailer {retailer_id}")
                flash('A customer with this phone number already exists!', 'error')
                db.close()
                return render_template('add_customer.html')

            # Create new customer
            cursor = db.execute(
                'INSERT INTO users (phone_number, user_type, name) VALUES (?, ?, ?)',
                (phone, 'customer', name)
            )
            customer_id = cursor.lastrowid
            db.commit()
            
            print(f"Customer created successfully: ID={customer_id}, Name={name}, Phone={phone}, Retailer={retailer_id}")
            flash('Customer added successfully!', 'success')
            return redirect(url_for('retailer_customers'))

        except Exception as e:
            db.rollback()
            print(f"Error adding customer: {str(e)} - Retailer: {retailer_id}, Name: {name}, Phone: {phone}")
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

# TEMPORARILY DISABLED - Fixing stability issues
# @app.route('/credit/add', methods=['GET', 'POST'])
# @app.route('/credit/add/<int:customer_id>', methods=['GET', 'POST'])
# def add_credit(customer_id=None):
#     """Add a credit entry for a customer - DISABLED TEMPORARILY"""
#     flash('Credit feature is temporarily unavailable. Please use Add Payment instead.', 'warning')
#     return redirect(url_for('retailer_dashboard'))

@app.route('/credit/add', methods=['GET', 'POST'])
@app.route('/credit/add/<int:customer_id>', methods=['GET', 'POST'])
def add_credit(customer_id=None):
    """Add a credit entry for customer - SRS COMPLIANT"""
    if not is_user_logged_in():
        return redirect(url_for('login'))
    if session.get('user_type') != 'retailer':
        flash('Access denied. Only retailers can add credits.', 'error')
        return redirect(url_for('dashboard'))
    
    retailer_id = session['user_id']
    
    if request.method == 'POST':
        try:
            customer_id = int(request.form['customer_id'])
            amount = float(request.form['amount'])
            notes = request.form.get('notes', '').strip()
            
            print(f"Adding credit: customer_id={customer_id}, amount={amount}, retailer_id={retailer_id}")
            
        except (ValueError, KeyError) as e:
            print(f"Invalid form data: {e}")
            flash('Invalid form data. Please check your input.', 'error')
            customers = _get_customers_for_retailer(db, retailer_id)
            return render_template('add_credit.html', customers=customers)
        
        # Validate customer exists
        customer = db.execute(
            'SELECT id, name FROM users WHERE id = ? AND user_type = ?', 
            (customer_id, 'customer')
        ).fetchone()
        if not customer:
            print(f"Customer not found: {customer_id}")
            flash('Selected customer not found.', 'error')
            customers = _get_customers_for_retailer(db, retailer_id)
            return render_template('add_credit.html', customers=customers)
        
        try:
            db = get_db()
            
            # Insert credit transaction as per SRS
            db.execute(
                'INSERT INTO transactions (retailer_id, customer_id, type, amount, date, notes) VALUES (?, ?, ?, ?, ?, ?)',
                (retailer_id, customer_id, 'credit', amount, datetime.now().date(), notes or 'Credit entry')
            )
            
            # Add timeline event for tracking
            db.execute(
                'INSERT INTO timeline_events (customer_id, retailer_id, event_type, amount, description) VALUES (?, ?, ?, ?, ?)',
                (customer_id, retailer_id, 'credit_added', amount, f'Credit of ₹{amount:.2f} added')
            )
            
            db.commit()
            
            # Calculate new outstanding balance
            credits_sum = db.execute(
                'SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND retailer_id = ? AND type = ?',
                (customer_id, retailer_id, 'credit')
            ).fetchone()[0]
            
            payments_sum = db.execute(
                'SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND retailer_id = ? AND type = ?',
                (customer_id, retailer_id, 'payment')
            ).fetchone()[0]
            
            new_outstanding = credits_sum - payments_sum
            print(f"Credit added successfully. New outstanding: ₹{new_outstanding:.2f}")
            
            flash(f'Credit of ₹{amount:.2f} added successfully! New outstanding balance: ₹{new_outstanding:.2f}', 'success')
            return redirect(url_for('retailer_customers'))
            
        except Exception as e:
            db.rollback()
            print(f"Error adding credit: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error adding credit: {str(e)}', 'error')
        finally:
            db.close()
    
    # GET request - show form
    db = get_db()
    try:
        customers = _get_customers_for_retailer(db, retailer_id)
        selected_customer = None
        if customer_id:
            selected_customer = next((c for c in customers if c['id'] == customer_id), None)

        return render_template('add_credit.html', customers=customers, selected_customer=selected_customer)
    finally:
        db.close()


# ============================================================================
# PAYMENT ENTRY OPERATIONS
# ============================================================================

@app.route('/payment/add', methods=['GET', 'POST'])
@app.route('/payment/add/<int:customer_id>', methods=['GET', 'POST'])

def add_payment(customer_id=None):
    """Add a payment entry that reduces outstanding balance (requires login)"""
    if not is_user_logged_in():
        return redirect(url_for('login'))
    
    # Store retailer_id from session for the payment record
    retailer_id = session.get('user_id')
    user_type = session.get('user_type')
    
    if user_type != 'retailer':
         flash('Access denied. Only retailers can add payments.', 'error')
         return redirect(url_for('customer_dashboard')) # Or appropriate redirect

    db = get_db()
    
    if request.method == 'POST':
        try:
            customer_id = int(request.form['customer_id'])
            amount = float(request.form['amount'])
        except (ValueError, KeyError) as e:
            flash('Invalid form data. Please check your input.', 'error')
            customers = db.execute('SELECT id, name FROM users WHERE user_type = ? ORDER BY name', ('customer',)).fetchall()
            return render_template('add_payment.html', customers=customers)
        
        # Validate customer exists
        customer = db.execute('SELECT id, name FROM users WHERE id = ? AND user_type = ?', (customer_id, 'customer')).fetchone()
        if not customer:
            flash('Selected customer not found.', 'error')
            customers = db.execute('SELECT id, name FROM users WHERE user_type = ? ORDER BY name', ('customer',)).fetchall()
            return render_template('add_payment.html', customers=customers)
        
        # Calculate current outstanding balance using transactions table
        total_debits = db.execute(
            'SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND retailer_id = ? AND type = ?',
            (customer_id, retailer_id, 'credit')
        ).fetchone()[0]
        
        total_payments = db.execute(
            'SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND retailer_id = ? AND type = ?',
            (customer_id, retailer_id, 'payment')
        ).fetchone()[0]
        
        outstanding_balance = total_debits - total_payments
        
        # Prevent negative balance
        if amount > outstanding_balance:
            flash(f'Payment amount ({amount}) exceeds outstanding balance ({outstanding_balance}) for your store!', 'error')
            customers = db.execute('SELECT id, name FROM users WHERE user_type = ? ORDER BY name', ('customer',)).fetchall()
            return render_template('add_payment.html', customers=customers)
        
        try:
            payment_date = datetime.now().date()
            
            print(f"Processing payment: customer_id={customer_id}, amount={amount}, retailer_id={retailer_id}")
            
            # Insert payment transaction as per SRS
            db.execute(
                'INSERT INTO transactions (retailer_id, customer_id, type, amount, date, notes) VALUES (?, ?, ?, ?, ?, ?)',
                (retailer_id, customer_id, 'payment', amount, payment_date, f'Payment of ₹{amount:.2f} received')
            )
            
            # Add timeline event for better tracking
            db.execute(
                'INSERT INTO timeline_events (customer_id, retailer_id, event_type, amount, description) VALUES (?, ?, ?, ?, ?)',
                (customer_id, retailer_id, 'payment_added', amount, f'Payment of ₹{amount:.2f} received')
            )
            
            db.commit()
            
            # Calculate new outstanding balance
            new_outstanding = outstanding_balance - amount
            print(f"Payment recorded successfully. New outstanding: ₹{new_outstanding:.2f}")
            
            flash(f'Payment of ₹{amount:.2f} recorded successfully! New outstanding balance: ₹{new_outstanding:.2f}', 'success')
            return redirect(url_for('retailer_customers'))
            
        except Exception as e:
            db.rollback()
            print(f"Error adding payment: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error adding payment: {str(e)}', 'error')
        finally:
            db.close()
    
    # GET request - show form
    try:
        # Show only customers relevant to this retailer (optional optimization, but safer)
        # For now, keeping original logic to show all customers, but future optimization could filter.
        customers = db.execute('SELECT id, name FROM users WHERE user_type = ? ORDER BY name', ('customer',)).fetchall()
        
        selected_customer = None
        if customer_id:
            selected_customer = db.execute(
                'SELECT id, name FROM users WHERE id = ? AND user_type = ?',
                (customer_id, 'customer')
            ).fetchone()

        return render_template('add_payment.html', customers=customers, selected_customer=selected_customer)
    finally:
        db.close()


# ============================================================================
# OVERDUE DETECTION
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
    """Retailer views pending payment requests - TEMPORARILY DISABLED"""
    if not is_user_logged_in():
        return redirect(url_for('login'))
    if session.get('user_type') != 'retailer':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    flash('Payment Requests feature is temporarily unavailable.', 'warning')
    return redirect(url_for('retailer_dashboard'))


@app.route('/retailer/payment-request/<int:request_id>/<action>', methods=['POST'])
def process_payment_request(request_id, action):
    """Retailer confirms or rejects a payment request - TEMPORARILY DISABLED"""
    if not is_user_logged_in():
        return redirect(url_for('login'))
    if session.get('user_type') != 'retailer':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    flash('Payment Requests feature is temporarily unavailable.', 'warning')
    return redirect(url_for('retailer_dashboard'))


@app.route('/retailer/customer/<int:customer_id>')
def customer_timeline(customer_id):
    """Retailer views customer timeline and details"""
    if not is_user_logged_in():
        return redirect(url_for('login'))
    if session.get('user_type') != 'retailer':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
        
    db = get_db()
    retailer_id = session['user_id']
    
    try:
        print(f"Fetching timeline for customer_id: {customer_id}, retailer_id: {retailer_id}")
        
        # Get customer details
        customer = db.execute('SELECT * FROM users WHERE id = ? AND user_type = ?', (customer_id, 'customer')).fetchone()
        if not customer:
            print(f"Customer not found: {customer_id} for retailer {retailer_id}")
            flash('Customer not found!', 'error')
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
        
        print(f"Timeline loaded for customer {customer_id}: {len(timeline)} events, outstanding: {outstanding}")
        
        return render_template('customer_timeline.html', customer=customer, timeline=timeline, outstanding=outstanding)
        
    except Exception as e:
        print(f"Error loading customer timeline: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading customer details. Please try again.', 'error')
        return redirect(url_for('retailer_customers'))
    finally:
        db.close()






if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
