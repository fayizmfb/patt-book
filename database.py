"""
Patt Book - Retailer Only Database Schema
WhatsApp OTP Authentication & Ledger System
"""

import sqlite3
import os
from datetime import datetime, timedelta
import hashlib

DATABASE_PATH = 'retail_app.db'

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize database with Retailer-Only schema"""
    db = get_db()
    
    # Drop all existing tables for clean start
    db.execute('DROP TABLE IF EXISTS otp_requests')
    db.execute('DROP TABLE IF EXISTS transactions')
    db.execute('DROP TABLE IF EXISTS debtors')
    db.execute('DROP TABLE IF EXISTS retailers')
    db.execute('DROP TABLE IF EXISTS sessions')
    db.execute('DROP TABLE IF EXISTS otp_rate_limits')
    db.execute('DROP TABLE IF EXISTS audit_logs')
    
    # Create retailers table
    db.execute('''
        CREATE TABLE retailers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            shop_name TEXT NOT NULL,
            shop_address TEXT NOT NULL,
            shop_photo_url TEXT,
            pin_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create debtors table
    db.execute('''
        CREATE TABLE debtors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            retailer_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            total_due REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (retailer_id) REFERENCES retailers (id)
        )
    ''')
    
    # Create transactions table
    db.execute('''
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            debtor_id INTEGER NOT NULL,
            type TEXT CHECK(type IN ('credit', 'payment')) NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (debtor_id) REFERENCES debtors (id)
        )
    ''')
    
    # Create OTP requests table with rate limiting
    db.execute('''
        CREATE TABLE otp_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            otp_hash TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            attempts INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(phone)
        )
    ''')
    
    # Create sessions table for device tracking
    db.execute('''
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            retailer_id INTEGER NOT NULL,
            device_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (retailer_id) REFERENCES retailers (id),
            UNIQUE(retailer_id, device_id)
        )
    ''')
    
    # Create rate limiting table for OTP attempts
    db.execute('''
        CREATE TABLE otp_rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            attempt_count INTEGER DEFAULT 1,
            window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_blocked BOOLEAN DEFAULT 0,
            block_until TIMESTAMP,
            UNIQUE(phone, window_start)
        )
    ''')
    
    # Create audit logs table
    db.execute('''
        CREATE TABLE audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            retailer_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (retailer_id) REFERENCES retailers (id)
        )
    ''')
    
    # Create indexes for performance
    db.execute('CREATE INDEX idx_debtors_retailer_id ON debtors(retailer_id)')
    db.execute('CREATE INDEX idx_transactions_debtor_id ON transactions(debtor_id)')
    db.execute('CREATE INDEX idx_otp_requests_phone ON otp_requests(phone)')
    
    db.commit()
    db.close()
    print("Database initialized with Retailer-Only schema")

def hash_otp(otp):
    """Hash OTP for secure storage"""
    return hashlib.sha256(otp.encode()).hexdigest()

def cleanup_expired_otps():
    """Clean up expired OTPs"""
    db = get_db()
    try:
        db.execute('DELETE FROM otp_requests WHERE expires_at < ?', (datetime.now(),))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error cleaning expired OTPs: {e}")
    finally:
        db.close()

def check_otp_rate_limit(phone):
    """Check if phone is rate limited for OTP requests"""
    db = get_db()
    try:
        current_time = datetime.now()
        window_start = current_time - timedelta(minutes=10)
        
        # Clean old rate limit records
        db.execute('DELETE FROM otp_rate_limits WHERE window_start < ?', (window_start,))
        
        # Check current window attempts
        rate_record = db.execute(
            'SELECT attempt_count, is_blocked, block_until FROM otp_rate_limits WHERE phone = ? AND window_start >= ?',
            (phone, window_start)
        ).fetchone()
        
        if rate_record and rate_record['is_blocked']:
            if current_time < datetime.fromisoformat(rate_record['block_until']):
                return {
                    'blocked': True,
                    'block_until': rate_record['block_until'],
                    'message': 'Too many OTP attempts. Please try again later.'
                }
        
        if rate_record and rate_record['attempt_count'] >= 3:
            # Block for 15 minutes
            block_until = current_time + timedelta(minutes=15)
            db.execute(
                'UPDATE otp_rate_limits SET is_blocked = 1, block_until = ? WHERE phone = ? AND window_start >= ?',
                (block_until, phone, window_start)
            )
            db.commit()
            return {
                'blocked': True,
                'block_until': block_until.isoformat(),
                'message': 'Too many OTP attempts. Please try again in 15 minutes.'
            }
        
        return {'blocked': False}
        
    except Exception as e:
        print(f"Error checking OTP rate limit: {e}")
        return {'blocked': False, 'error': str(e)}
    finally:
        db.close()

def record_otp_attempt(phone):
    """Record OTP attempt for rate limiting"""
    db = get_db()
    try:
        current_time = datetime.now()
        window_start = current_time - timedelta(minutes=10)
        
        # Update or create rate limit record
        existing = db.execute(
            'SELECT id FROM otp_rate_limits WHERE phone = ? AND window_start >= ?',
            (phone, window_start)
        ).fetchone()
        
        if existing:
            db.execute(
                'UPDATE otp_rate_limits SET attempt_count = attempt_count + 1 WHERE phone = ? AND window_start >= ?',
                (phone, window_start)
            )
        else:
            db.execute(
                'INSERT INTO otp_rate_limits (phone, attempt_count, window_start) VALUES (?, 1, ?)',
                (phone, current_time)
            )
        
        db.commit()
        
    except Exception as e:
        print(f"Error recording OTP attempt: {e}")
    finally:
        db.close()

def create_retailer_session(retailer_id, device_id, token):
    """Create new session and invalidate old sessions"""
    db = get_db()
    try:
        # Invalidate old sessions for this retailer
        db.execute(
            'UPDATE sessions SET is_active = 0 WHERE retailer_id = ?',
            (retailer_id,)
        )
        
        # Check if session already exists
        existing = db.execute(
            'SELECT id FROM sessions WHERE retailer_id = ? AND device_id = ?',
            (retailer_id, device_id)
        ).fetchone()
        
        if existing:
            # Update existing session
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            db.execute(
                'UPDATE sessions SET token_hash = ?, created_at = ?, last_active = ?, is_active = 1 WHERE id = ?',
                (token_hash, datetime.now(), datetime.now(), existing['id'])
            )
        else:
            # Create new session
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            db.execute(
                'INSERT INTO sessions (retailer_id, device_id, token_hash) VALUES (?, ?, ?)',
                (retailer_id, device_id, token_hash)
            )
        
        db.commit()
        return True
        
    except Exception as e:
        print(f"Error creating session: {e}")
        return False
    finally:
        db.close()

def validate_session(retailer_id, token, device_id):
    """Validate session and check device"""
    db = get_db()
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        session = db.execute(
            'SELECT * FROM sessions WHERE retailer_id = ? AND token_hash = ? AND device_id = ? AND is_active = 1',
            (retailer_id, token_hash, device_id)
        ).fetchone()
        
        if session:
            # Update last active time
            db.execute(
                'UPDATE sessions SET last_active = ? WHERE id = ?',
                (datetime.now(), session['id'])
            )
            db.commit()
            return True
        
        return False
        
    except Exception as e:
        print(f"Error validating session: {e}")
        return False
    finally:
        db.close()

def log_audit_action(retailer_id, user_id, action, details=None, ip_address=None, user_agent=None):
    """Log audit action for compliance"""
    db = get_db()
    try:
        db.execute(
            'INSERT INTO audit_logs (retailer_id, user_id, action, details, ip_address, user_agent) VALUES (?, ?, ?, ?, ?, ?)',
            (retailer_id, user_id, action, details, ip_address, user_agent)
        )
        db.commit()
        return True
    except Exception as e:
        print(f"Error logging audit action: {e}")
        return False
    finally:
        db.close()

def create_retailer_with_pin(phone, shop_name, shop_address, pin_hash):
    """Create new retailer with PIN"""
    db = get_db()
    try:
        cursor = db.execute(
            'INSERT INTO retailers (phone, shop_name, shop_address, pin_hash) VALUES (?, ?, ?, ?)',
            (phone, shop_name, shop_address, pin_hash)
        )
        db.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None  # Phone already exists
    except Exception as e:
        print(f"Error creating retailer: {e}")
        return None
    finally:
        db.close()

def get_retailer_by_phone(phone):
    """Get retailer by phone number"""
    db = get_db()
    try:
        retailer = db.execute(
            'SELECT * FROM retailers WHERE phone = ?',
            (phone,)
        ).fetchone()
        return retailer
    except Exception as e:
        print(f"Error getting retailer: {e}")
        return None
    finally:
        db.close()

def update_retailer_pin(retailer_id, pin_hash):
    """Update retailer PIN"""
    db = get_db()
    try:
        db.execute(
            'UPDATE retailers SET pin_hash = ? WHERE id = ?',
            (pin_hash, retailer_id)
        )
        db.commit()
        return True
    except Exception as e:
        print(f"Error updating PIN: {e}")
        return False
    finally:
        db.close()

if __name__ == '__main__':
    init_db()
