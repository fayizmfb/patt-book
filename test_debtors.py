import sqlite3
from datetime import datetime

# Test the query logic directly
conn = sqlite3.connect('retail_app.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
today = datetime.now().date()

debtor_data = cursor.execute('''
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
''', (today, today)).fetchall()

print(f'Query returned {len(debtor_data)} debtors:')
for row in debtor_data:
    outstanding = max(0, row['total_credits'] - row['total_payments'])
    print(f'  {row["customer_name"]}: outstanding=${outstanding:.2f}, next_due={row["next_due_date"]}, overdue_count={row["overdue_count"]}')

conn.close()