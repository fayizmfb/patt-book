"""
Patt Book Database Schema
Email OTP Authentication with Phone as Unique Identifier
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
    """Initialize database with Email OTP schema"""
    db = get_db()
    
    # Drop existing tables if they exist
    db.execute('DROP TABLE IF EXISTS email_otps')
    db.execute('DROP TABLE IF EXISTS customers')
    db.execute('DROP TABLE IF EXISTS retailers')
    db.execute('DROP TABLE IF EXISTS transactions')
    db.execute('DROP TABLE IF EXISTS fcm_tokens')
    
    # Create retailers table
    db.execute('''
        CREATE TABLE retailers (
            retailer_phone TEXT PRIMARY KEY,
            shop_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            email_verified BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create customers table
    db.execute('''
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            email_verified BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create transactions table
    db.execute('''
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            retailer_phone TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            type TEXT CHECK(type IN ('credit','payment')) NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            notes TEXT
        )
    ''')
    
    # Create FCM tokens table for push notifications
    db.execute('''
        CREATE TABLE fcm_tokens (
            customer_phone TEXT NOT NULL,
            token TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (customer_phone, token)
        )
    ''')
    
    # Create email OTPs table
    db.execute('''
        CREATE TABLE email_otps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            otp_hash TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            attempts INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(email)
        )
    ''')
    
    db.commit()
    db.close()
    print("Database initialized with Email OTP schema")

def hash_otp(otp):
    """Hash OTP for secure storage"""
    return hashlib.sha256(otp.encode()).hexdigest()

if __name__ == '__main__':
    init_db()