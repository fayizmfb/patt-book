"""
Patt Book - Production Database Schema
Role-based authentication for Retailer and Customer
"""

import sqlite3
import os
from datetime import datetime, timedelta

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

# User management functions
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

# Customer management functions
def add_customer(retailer_id, customer_name, mobile_number, due_amount=0.0, description=None):
    """Add a customer to retailer's list"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO customers 
        (retailer_id, customer_name, mobile_number, due_amount, description)
        VALUES (?, ?, ?, ?, ?)
    ''', (retailer_id, customer_name, mobile_number, due_amount, description))
    
    customer_id = cursor.lastrowid
    db.commit()
    db.close()
    return customer_id

def get_retailer_customers(retailer_id, search=None, sort_by='name'):
    """Get retailer's customers with optional search and sorting"""
    db = get_db()
    
    query = 'SELECT * FROM customers WHERE retailer_id = ?'
    params = [retailer_id]
    
    if search:
        query += ' AND customer_name LIKE ?'
        params.append(f'%{search}%')
    
    if sort_by == 'amount':
        query += ' ORDER BY due_amount DESC'
    elif sort_by == 'name':
        query += ' ORDER BY customer_name ASC'
    
    customers = db.execute(query, params).fetchall()
    db.close()
    return customers

def update_customer_due(customer_id, amount, transaction_type):
    """Update customer due amount"""
    db = get_db()
    cursor = db.cursor()
    
    if transaction_type == 'credit':
        cursor.execute('''
            UPDATE customers 
            SET due_amount = due_amount + ?,
                total_credit = total_credit + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (amount, amount, customer_id))
    elif transaction_type == 'payment':
        cursor.execute('''
            UPDATE customers 
            SET due_amount = due_amount - ?,
                total_paid = total_paid + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (amount, amount, customer_id))
    
    db.commit()
    db.close()

# Transaction functions
def add_transaction(customer_id, retailer_id, transaction_type, amount, description=None):
    """Add a transaction"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        INSERT INTO transactions (customer_id, retailer_id, type, amount, description)
        VALUES (?, ?, ?, ?, ?)
    ''', (customer_id, retailer_id, transaction_type, amount, description))
    
    transaction_id = cursor.lastrowid
    db.commit()
    db.close()
    return transaction_id

def get_customer_transactions(customer_id):
    """Get transaction history for a customer"""
    db = get_db()
    transactions = db.execute(
        'SELECT * FROM transactions WHERE customer_id = ? ORDER BY created_at DESC',
        (customer_id,)
    ).fetchall()
    db.close()
    return transactions

# Session management
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

def validate_session(token):
    """Validate a session token"""
    db = get_db()
    session = db.execute(
        '''SELECT s.*, u.* FROM sessions s 
           JOIN users u ON s.user_id = u.id 
           WHERE s.token = ? AND s.expires_at > CURRENT_TIMESTAMP''',
        (token,)
    ).fetchone()
    db.close()
    return session

def revoke_session(token):
    """Revoke a session"""
    db = get_db()
    db.execute('DELETE FROM sessions WHERE token = ?', (token,))
    db.commit()
    db.close()

# OTP functions
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
    
    otp_request = db.execute(
        '''SELECT * FROM otp_requests 
           WHERE mobile_number = ? AND otp = ? 
           AND expires_at > CURRENT_TIMESTAMP AND is_used = FALSE
           ORDER BY created_at DESC LIMIT 1''',
        (mobile_number, otp)
    ).fetchone()
    
    if otp_request:
        # Mark OTP as used
        db.execute(
            'UPDATE otp_requests SET is_used = TRUE WHERE id = ?',
            (otp_request['id'],)
        )
        db.commit()
    
    db.close()
    return otp_request is not None
