"""
Database initialization and connection management
Handles SQLite database setup and provides connection helper
"""

import sqlite3

DATABASE = 'retail_app.db'


def init_db():
    """
    Initialize the database with required tables:
    - customers: Customer master data
    - credits: Credit entries with due dates
    - payments: Payment entries
    """
    conn = get_db()
    try:
        # Create customers table (Customer Master)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create credits table (Credit Entries)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS credits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                entry_date DATE NOT NULL,
                due_days INTEGER,
                due_date DATE,
                reminder_date DATE,
                whatsapp_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers (id)
            )
        """)
        
        # Add new columns to credits table if they don't exist (migration)
        try:
            conn.execute("ALTER TABLE credits ADD COLUMN reminder_date DATE")
        except:
            pass  # Column might already exist
        
        try:
            conn.execute("ALTER TABLE credits ADD COLUMN whatsapp_message TEXT")
        except:
            pass  # Column might already exist
        
        # Migration: Make due_days and due_date nullable (for simplified reminder logic)
        try:
            # Check if due_days is still NOT NULL by attempting to insert a test row
            # If it fails, we need to recreate the table
            cursor = conn.execute("PRAGMA table_info(credits)")
            columns = cursor.fetchall()
            
            # Find due_days column
            due_days_not_null = False
            due_date_not_null = False
            for col in columns:
                if col[1] == 'due_days' and col[3] == 1:  # col[3] is notnull
                    due_days_not_null = True
                if col[1] == 'due_date' and col[3] == 1:  # col[3] is notnull
                    due_date_not_null = True
            
            # If either column is still NOT NULL, recreate the table
            if due_days_not_null or due_date_not_null:
                print("Migrating credits table to make due_days and due_date nullable...")
                
                # Create new table with updated schema
                conn.execute("""
                    CREATE TABLE credits_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_id INTEGER NOT NULL,
                        amount REAL NOT NULL,
                        entry_date DATE NOT NULL,
                        due_days INTEGER,
                        due_date DATE,
                        reminder_date DATE,
                        whatsapp_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (customer_id) REFERENCES customers (id)
                    )
                """)
                
                # Copy data from old table to new table
                conn.execute("""
                    INSERT INTO credits_new 
                    (id, customer_id, amount, entry_date, due_days, due_date, reminder_date, whatsapp_message, created_at)
                    SELECT id, customer_id, amount, entry_date, due_days, due_date, reminder_date, whatsapp_message, created_at
                    FROM credits
                """)
                
                # Drop old table and rename new table
                conn.execute("DROP TABLE credits")
                conn.execute("ALTER TABLE credits_new RENAME TO credits")
                
                print("Migration completed successfully!")
        
        except Exception as e:
            print(f"Migration check failed (this is normal for new databases): {e}")
        
        # Create payments table (Payment Entries)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                payment_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers (id)
            )
        """)
        
        # Create transactions table (Unified transaction history)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('DEBIT', 'PAYMENT')),
                amount REAL NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers (id)
            )
        """)
        
        # Create settings table (for admin configuration)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default settings if they don't exist
        default_settings = [
            ('default_dunning_days', '15', 'Default number of days from entry date until payment is due'),
            ('app_name', 'Retail App', 'Application name'),
            ('app_description', 'Simple accounting system for small retailers', 'Application description'),
            ('admin_email', '', 'Admin email address'),
            ('admin_phone', '', 'Admin phone number'),
            ('store_name', 'Your Store', 'Store name (used in WhatsApp messages)'),
            ('store_address', '', 'Store address'),
            ('store_email', '', 'Store email address'),
            ('whatsapp_api_url', '', 'WhatsApp Business API base URL'),
            ('whatsapp_api_token', '', 'WhatsApp Business API access token'),
            ('whatsapp_phone_id', '', 'WhatsApp Business Phone Number ID')
        ]
        
        for key, value, description in default_settings:
            conn.execute("""
                INSERT OR IGNORE INTO settings (key, value, description)
                VALUES (?, ?, ?)
            """, (key, value, description))
        
        # Create retailers table (Master list of all retailers)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS retailers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                phone_number TEXT NOT NULL,
                store_name TEXT NOT NULL,
                store_address TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active_date DATE,
                last_login_date TIMESTAMP
            )
        """)
        
        # Create admin_users table (Admin authentication)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # Create audit_logs table (Admin activity tracking)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_user TEXT,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create announcements table (Admin communications to retailers)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        """)
        
        # Create system_settings table (Global app settings)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default system settings
        system_settings = [
            ('global_dunning_days', '15', 'Global default dunning days for all retailers'),
            ('disclaimer_text', 'Patt Book does NOT collect payments. Do NOT make payments through any links.', 'Default disclaimer text'),
            ('whatsapp_enabled', 'true', 'Enable/disable WhatsApp messaging globally'),
            ('app_maintenance_mode', 'false', 'Maintenance mode for the entire app')
        ]
        
        for key, value, description in system_settings:
            conn.execute("""
                INSERT OR IGNORE INTO system_settings (key, value, description)
                VALUES (?, ?, ?)
            """, (key, value, description))
        
        # Create default admin user (username: admin, password: admin123)
        # In production, change this password immediately!
        import hashlib
        default_password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
        conn.execute("""
            INSERT OR IGNORE INTO admin_users (username, password_hash, email)
            VALUES ('admin', ?, 'admin@pattbook.com')
        """, (default_password_hash,))
        
        # Create indexes for better query performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_credits_customer ON credits(customer_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions(customer_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_retailers_user_id ON retailers(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_retailers_status ON retailers(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_admin ON audit_logs(admin_user)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at)")
        
        conn.commit()
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

