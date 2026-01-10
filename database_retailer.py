"""
Patt Book - Retailer Only Database Schema
WhatsApp OTP Authentication & Ledger System
"""

import sqlite3
import os
from datetime import datetime
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
    
    # Create retailers table
    db.execute('''
        CREATE TABLE retailers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            shop_name TEXT NOT NULL,
            shop_address TEXT NOT NULL,
            shop_photo_url TEXT,
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
    
    # Create OTP requests table
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
        print(f"Error cleaning up expired OTPs: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    init_db()
