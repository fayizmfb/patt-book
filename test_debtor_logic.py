from app import debtor_details
from unittest.mock import Mock
import sqlite3
from datetime import datetime

# Mock the request and session for testing
mock_request = Mock()
mock_request.args.get.return_value = 'due_asc'

# Mock session
import app
app.session = {}

# Test the debtor_details function directly
try:
    # This will fail because of database connection, but let's see the logic
    result = debtor_details()
    print("Function executed successfully")
except Exception as e:
    print(f"Function error: {e}")

# Test the logic more directly
print("\nTesting debtor logic...")

# Simulate the route logic
db = sqlite3.connect('retail_app.db')
db.row_factory = sqlite3.Row
today = datetime.now().date()

# Get sort option
sort_option = 'due_asc'

# Get all customers with outstanding balance > 0
debtor_data = db.execute("""
    SELECT
        cust.id as customer_id,
        cust.name as customer_name,
        cust.phone,
        (SELECT COALESCE(SUM(amount), 0) FROM credits WHERE customer_id = cust.id) as total_credits,
        (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE customer_id = cust.id) as total_payments,
        (SELECT MIN(due_date) FROM credits WHERE customer_id = cust.id AND due_date >= ?) as next_due_date,
        (SELECT COUNT(*) FROM credits WHERE customer_id = cust.id AND due_date < ?) as overdue_count
    FROM customers cust
    WHERE (SELECT COALESCE(SUM(amount), 0) FROM credits WHERE customer_id = cust.id) -
          (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE customer_id = cust.id) > 0
    ORDER BY cust.name
""", (today, today)).fetchall()

print(f"Found {len(debtor_data)} debtors")

# Build debtor list
debtor_list = []
for row in debtor_data:
    outstanding_balance = max(0, row['total_credits'] - row['total_payments'])
    next_due_date = row['next_due_date']
    if not next_due_date:
        # If no future due dates, get the most recent past due date
        past_due = db.execute("""
            SELECT MAX(due_date) FROM credits
            WHERE customer_id = ? AND due_date < ?
        """, (row['customer_id'], today)).fetchone()[0]
        next_due_date = past_due

    if next_due_date:
        if isinstance(next_due_date, str):
            due_date_obj = datetime.strptime(next_due_date, '%Y-%m-%d').date()
        else:
            due_date_obj = next_due_date

        days_until_due = (due_date_obj - today).days

        if days_until_due < 0:
            status = 'overdue'
            days_overdue = abs(days_until_due)
            if days_overdue <= 7:
                bucket = '0-7 days'
            elif days_overdue <= 10:
                bucket = '8-10 days'
            elif days_overdue <= 15:
                bucket = '11-15 days'
            elif days_overdue <= 20:
                bucket = '16-20 days'
            elif days_overdue <= 25:
                bucket = '21-25 days'
            elif days_overdue <= 30:
                bucket = '26-30 days'
            elif days_overdue <= 45:
                bucket = '31-45 days'
            else:
                bucket = 'Over 45 days'
        else:
            status = 'current'
            days_overdue = 0
            if days_until_due <= 7:
                bucket = 'Due within 7 days'
            elif days_until_due <= 14:
                bucket = 'Due within 14 days'
            elif days_until_due <= 30:
                bucket = 'Due within 30 days'
            else:
                bucket = 'Due in 30+ days'

        debtor_list.append({
            'customer_id': row['customer_id'],
            'customer_name': row['customer_name'],
            'phone': row['phone'],
            'outstanding_balance': outstanding_balance,
            'due_date': next_due_date,
            'days_until_due': days_until_due,
            'days_overdue': days_overdue,
            'status': status,
            'bucket': bucket,
            'overdue_count': row['overdue_count']
        })

print(f"Built debtor list with {len(debtor_list)} items:")
for debtor in debtor_list:
    print(f"  {debtor['customer_name']}: ${debtor['outstanding_balance']:.2f}, status={debtor['status']}, bucket={debtor['bucket']}")

db.close()