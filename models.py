"""
Data models and helper functions
This file contains data structures and utility functions for the accounting system
"""

# Note: This file is kept simple as we're using raw SQL queries.
# In a larger application, you might use an ORM like SQLAlchemy here.

from datetime import datetime, timedelta
from database import get_db


def calculate_due_date(entry_date, due_days):
    """
    Calculate the due date based on entry date and due days.
    
    Args:
        entry_date: The date when credit was entered (datetime.date)
        due_days: Number of days until due (int, should be 5-30)
    
    Returns:
        datetime.date: The calculated due date
    """
    if due_days < 5 or due_days > 30:
        raise ValueError("Due days must be between 5 and 30")
    
    return entry_date + timedelta(days=due_days)


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
    
    return float(total_credits) - float(total_payments)


def get_overdue_credits():
    """
    Get all credits that are overdue (due_date < today and balance > 0).
    
    Returns:
        list: List of overdue credit records
    """
    db = get_db()
    today = datetime.now().date()
    
    overdue = db.execute("""
        SELECT 
            c.id,
            c.customer_id,
            c.amount,
            c.due_date,
            (c.amount - COALESCE(SUM(p.amount), 0)) as outstanding_balance
        FROM credits c
        LEFT JOIN payments p ON c.customer_id = p.customer_id
        WHERE c.due_date < ?
        GROUP BY c.id
        HAVING outstanding_balance > 0
    """, (today,)).fetchall()
    
    return overdue

