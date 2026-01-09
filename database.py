"""
Database initialization and connection management
Handles SQLite database setup and provides connection helper
FIXED: Phone-number based schema for Patt Book
"""

import sqlite3

DATABASE = 'retail_app.db'


def init_db():
    """
    Initialize database with required tables:
    - retailers: Retailer master data
    - customers: Customer master data  
    - transactions: Unified ledger (credit/payment)
    """
    conn = get_db()
    try:
        # Create retailers table (Retailer Master)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS retailers (
                retailer_phone TEXT PRIMARY KEY,
                shop_name TEXT NOT NULL,
                store_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create customers table (Customer Master)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_phone TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                retailer_phone TEXT NOT NULL,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (retailer_phone) REFERENCES retailers(retailer_phone)
            )
        """)
        
        # Create transactions table (Unified Ledger)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                retailer_phone TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('credit', 'payment')),
                amount REAL NOT NULL,
                date DATE NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (retailer_phone) REFERENCES retailers(retailer_phone),
                FOREIGN KEY (customer_phone) REFERENCES customers(customer_phone)
            )
        """)
        
        # Create fcm_tokens table for push notifications
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fcm_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_phone TEXT NOT NULL,
                token TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_phone) REFERENCES customers(customer_phone)
            )
        """)
        
        # Create indexes for better query performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_retailer ON transactions(retailer_phone)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions(customer_phone)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_customers_retailer ON customers(retailer_phone)")
        
        conn.commit()
        print("Database initialized successfully with phone-number based schema")
        
    except Exception as e:
        print(f"Database initialization error: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_db():
    """
    Get a database connection.
    Uses row_factory to return rows as dictionaries for easier access.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access to rows
    return conn
