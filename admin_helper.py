"""
Admin Helper Functions
Handles admin authentication, retailer tracking, and admin operations
"""

import hashlib
from datetime import datetime
from database import get_db


def hash_password(password):
    """Hash password using SHA256 (simple hashing for demo - use bcrypt in production)"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_admin_login(username, password):
    """
    Verify admin username and password
    
    Args:
        username: Admin username
        password: Admin password
    
    Returns:
        bool: True if credentials are valid, False otherwise
    """
    db = get_db()
    try:
        password_hash = hash_password(password)
        admin = db.execute(
            'SELECT id, username, email FROM admin_users WHERE username = ? AND password_hash = ?',
            (username, password_hash)
        ).fetchone()
        
        if admin:
            # Update last login
            db.execute(
                'UPDATE admin_users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
                (admin['id'],)
            )
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error verifying admin login: {str(e)}")
        return False
    finally:
        db.close()


def log_admin_action(admin_user, action, details=None, ip_address=None):
    """
    Log admin action to audit log
    
    Args:
        admin_user: Admin username
        action: Action performed
        details: Additional details (optional)
        ip_address: IP address (optional)
    """
    db = get_db()
    try:
        db.execute("""
            INSERT INTO audit_logs (admin_user, action, details, ip_address)
            VALUES (?, ?, ?, ?)
        """, (admin_user, action, details, ip_address))
        db.commit()
    except Exception as e:
        print(f"Error logging admin action: {str(e)}")
    finally:
        db.close()


def get_retailer_stats():
    """
    Get overall statistics for admin dashboard
    
    Returns:
        dict: Statistics including total retailers, active/inactive, total customers, total outstanding
    """
    db = get_db()
    try:
        # Total retailers
        total_retailers = db.execute('SELECT COUNT(*) as count FROM retailers').fetchone()['count']
        
        # Active retailers
        active_retailers = db.execute(
            "SELECT COUNT(*) as count FROM retailers WHERE status = 'active'"
        ).fetchone()['count']
        
        # Inactive retailers
        inactive_retailers = total_retailers - active_retailers
        
        # Total customers (sum across all retailers - simplified, assumes one DB per retailer in production)
        # For multi-tenant, you'd need retailer_id in customers table
        total_customers = db.execute('SELECT COUNT(*) as count FROM customers').fetchone()['count']
        
        # Total outstanding amount
        total_credits = db.execute('SELECT COALESCE(SUM(amount), 0) FROM credits').fetchone()[0]
        total_payments = db.execute('SELECT COALESCE(SUM(amount), 0) FROM payments').fetchone()[0]
        total_outstanding = max(0, total_credits - total_payments)
        
        return {
            'total_retailers': total_retailers,
            'active_retailers': active_retailers,
            'inactive_retailers': inactive_retailers,
            'total_customers': total_customers,
            'total_outstanding': total_outstanding
        }
    except Exception as e:
        print(f"Error getting retailer stats: {str(e)}")
        return {
            'total_retailers': 0,
            'active_retailers': 0,
            'inactive_retailers': 0,
            'total_customers': 0,
            'total_outstanding': 0
        }
    finally:
        db.close()


def get_retailers_list(sort_by='newest'):
    """
    Get list of retailers with their statistics
    
    Args:
        sort_by: Sort option ('newest', 'most_customers', 'most_usage', 'recently_active')
    
    Returns:
        list: List of retailer dictionaries with stats
    """
    db = get_db()
    try:
        # Get all retailers
        retailers = db.execute("""
            SELECT 
                r.id,
                r.user_id,
                r.phone_number,
                r.store_name,
                r.store_address,
                r.status,
                r.created_at,
                r.last_active_date,
                r.last_login_date
            FROM retailers r
        """).fetchall()
        
        # Calculate stats for each retailer
        retailer_list = []
        for retailer in retailers:
            user_id = retailer['user_id']
            
            # For now, assuming single database - in production, would query per retailer
            # Count customers, credits, and outstanding for this retailer
            customer_count = db.execute('SELECT COUNT(*) as count FROM customers').fetchone()['count']
            credit_count = db.execute('SELECT COUNT(*) as count FROM credits').fetchone()['count']
            
            total_credits = db.execute('SELECT COALESCE(SUM(amount), 0) FROM credits').fetchone()[0]
            total_payments = db.execute('SELECT COALESCE(SUM(amount), 0) FROM payments').fetchone()[0]
            outstanding = total_credits - total_payments if (total_credits - total_payments) > 0 else 0
            
            retailer_list.append({
                'id': retailer['id'],
                'user_id': user_id,
                'phone_number': retailer['phone_number'],
                'store_name': retailer['store_name'],
                'store_address': retailer['store_address'],
                'status': retailer['status'],
                'customer_count': customer_count,
                'credit_count': credit_count,
                'outstanding_amount': outstanding,
                'created_at': retailer['created_at'],
                'last_active_date': retailer['last_active_date'],
                'last_login_date': retailer['last_login_date']
            })
        
        # Apply sorting
        if sort_by == 'most_customers':
            retailer_list.sort(key=lambda x: x['customer_count'], reverse=True)
        elif sort_by == 'most_usage':
            retailer_list.sort(key=lambda x: x['credit_count'], reverse=True)
        elif sort_by == 'newest':
            retailer_list.sort(key=lambda x: x['created_at'] or '', reverse=True)
        elif sort_by == 'recently_active':
            retailer_list.sort(key=lambda x: x['last_active_date'] or x['last_login_date'] or '', reverse=True)
        
        return retailer_list
    except Exception as e:
        print(f"Error getting retailers list: {str(e)}")
        return []
    finally:
        db.close()


def sync_retailer_from_firebase(user_id, phone_number, store_name, store_address):
    """
    Sync retailer data from Firebase to local database
    Called when retailer logs in or updates their info
    """
    db = get_db()
    try:
        # Check if retailer exists
        existing = db.execute(
            'SELECT id FROM retailers WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        
        if existing:
            # Update existing retailer
            db.execute("""
                UPDATE retailers 
                SET phone_number = ?, store_name = ?, store_address = ?, 
                    last_active_date = DATE('now'), last_login_date = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (phone_number, store_name, store_address, user_id))
        else:
            # Insert new retailer
            db.execute("""
                INSERT INTO retailers (user_id, phone_number, store_name, store_address, 
                                     last_active_date, last_login_date)
                VALUES (?, ?, ?, ?, DATE('now'), CURRENT_TIMESTAMP)
            """, (user_id, phone_number, store_name, store_address))
        
        db.commit()
        return True
    except Exception as e:
        print(f"Error syncing retailer: {str(e)}")
        return False
    finally:
        db.close()

