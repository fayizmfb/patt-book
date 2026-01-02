"""
Data models and helper functions
This file contains data structures and utility functions for the accounting system
"""

# Note: This file is kept simple as we're using raw SQL queries.
# In a larger application, you might use an ORM like SQLAlchemy here.

from datetime import datetime, timedelta
from database import get_db


def get_customer_balance(customer_id):
    """
    Calculate the outstanding balance for a customer.
    
    Args:
        customer_id: The ID of the customer (int)
    
    Returns:
        float: The outstanding balance (credits - payments)
    """
    db = get_db()
    
    total_credits = db.execute(
        'SELECT COALESCE(SUM(amount), 0) FROM credits WHERE customer_id = ?',
        (customer_id,)
    ).fetchone()[0]
    
    total_payments = db.execute(
        'SELECT COALESCE(SUM(amount), 0) FROM payments WHERE customer_id = ?',
        (customer_id,)
    ).fetchone()[0]
    
    return max(0, float(total_credits) - float(total_payments))

