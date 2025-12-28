"""
Standalone script to check and send WhatsApp reminders for due dates
Can be run as a scheduled task (cron job) to check daily for due payments

Usage:
    python send_reminders.py
"""

from datetime import datetime
from database import get_db
from whatsapp_helper import send_whatsapp_message, prepare_reminder_message, send_pre_due_reminders


def check_and_send_reminders():
    """
    Check for customers with due dates that have passed and outstanding balance > 0
    Send WhatsApp reminders to those customers (includes days overdue in message)
    """
    db = get_db()
    today = datetime.now().date()
    
    try:
        # Get store name from settings
        store_setting = db.execute(
            "SELECT value FROM settings WHERE key = 'store_name'"
        ).fetchone()
        store_name = store_setting['value'] if store_setting and store_setting['value'] else 'Your Store'
        
        # Find customers with due date <= today (overdue or due today) and outstanding balance > 0
        customers_to_remind = db.execute("""
            SELECT DISTINCT
                cust.id as customer_id,
                cust.name as customer_name,
                cust.phone,
                c.due_date
            FROM customers cust
            JOIN credits c ON c.customer_id = cust.id
            WHERE c.due_date <= ?
            AND cust.phone IS NOT NULL
            AND cust.phone != ''
        """, (today,)).fetchall()
        
        # Calculate actual outstanding balance and days overdue for each customer
        reminders_sent = 0
        for row in customers_to_remind:
            customer_id = row['customer_id']
            due_date_str = row['due_date']
            
            # Parse due date if it's a string
            if isinstance(due_date_str, str):
                from datetime import datetime as dt
                due_date = dt.strptime(due_date_str, '%Y-%m-%d').date()
            else:
                due_date = due_date_str
            
            # Calculate days overdue (0 if due today, >0 if past due)
            days_overdue = (today - due_date).days
            
            # Calculate actual outstanding balance
            total_credits = db.execute(
                'SELECT COALESCE(SUM(amount), 0) FROM credits WHERE customer_id = ?',
                (customer_id,)
            ).fetchone()[0]
            total_payments = db.execute(
                'SELECT COALESCE(SUM(amount), 0) FROM payments WHERE customer_id = ?',
                (customer_id,)
            ).fetchone()[0]
            outstanding_balance = total_credits - total_payments
            
            # Only send reminder if balance > 0
            if outstanding_balance > 0:
                try:
                    reminder_msg = prepare_reminder_message(
                        row['customer_name'],
                        store_name,
                        outstanding_balance,
                        due_date_str,
                        days_overdue
                    )
                    
                    if send_whatsapp_message(row['phone'], reminder_msg):
                        reminders_sent += 1
                        print(f"Overdue reminder sent to {row['customer_name']} ({row['phone']}) - {days_overdue} days overdue")
                except Exception as e:
                    print(f"Error sending overdue reminder to {row['customer_name']}: {str(e)}")
        
        print(f"Overdue reminder check completed. Sent {reminders_sent} reminder(s) for {today}")
        return reminders_sent
        
    except Exception as e:
        print(f"Error in overdue reminder check: {str(e)}")
        return 0
    finally:
        db.close()


if __name__ == '__main__':
    print(f"Checking for WhatsApp reminders on {datetime.now().date()}...")
    
    # Send pre-due reminders first
    print("Sending pre-due reminders...")
    pre_due_count = send_pre_due_reminders()
    
    # Then send overdue reminders
    print("Sending overdue reminders...")
    overdue_count = check_and_send_reminders()
    
    print(f"Total reminders sent: {pre_due_count + overdue_count} (Pre-due: {pre_due_count}, Overdue: {overdue_count})")

