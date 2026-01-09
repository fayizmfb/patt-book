"""
Patt Book Database Schema
Phone-number based authentication and ledger system
"""

import sqlite3
import os
from datetime import datetime

DATABASE_PATH = 'retail_app.db'

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize database with correct schema"""
    db = get_db()
    
    # Drop existing tables if they exist
    db.execute('DROP TABLE IF EXISTS transactions')
    db.execute('DROP TABLE IF EXISTS customers')
    db.execute('DROP TABLE IF EXISTS retailers')
    db.execute('DROP TABLE IF EXISTS fcm_tokens')
    
    # Create retailers table
    db.execute('''
        CREATE TABLE retailers (
            retailer_phone TEXT PRIMARY KEY,
            shop_name TEXT NOT NULL
        )
    ''')
    
    # Create customers table
    db.execute('''
        CREATE TABLE customers (
            retailer_phone TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_name TEXT NOT NULL
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
            date TEXT NOT NULL
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
    
    db.commit()
    db.close()
    print("Database initialized with correct phone-number schema")

if __name__ == '__main__':
    init_db()