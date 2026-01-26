"""
Patt Book - Sunday Reminder System
Automatically sends WhatsApp reminders to customers with pending balances
"""

import sqlite3
import requests
import schedule
import time
from datetime import datetime, timedelta
from database_new import get_db

# WhatsApp API Configuration
WHATSAPP_API_URL = "https://graph.facebook.com/v18.0/"
PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')

def get_customers_with_pending_dues():
    """Get all customers with pending dues for reminder"""
    db = get_db()
    
    # Get customers with due amounts > 0
    customers = db.execute('''
        SELECT 
            u.mobile_number as customer_mobile,
            u.customer_name,
            r.mobile_number as retailer_mobile,
            r.retailer_shop_name,
            c.due_amount,
            c.total_credit,
            c.created_at as customer_since
        FROM users u
        JOIN customers c ON u.id = c.retailer_id
        JOIN users r ON c.retailer_id = r.id
        WHERE u.user_type = 'retailer' 
        AND c.due_amount > 0
        AND c.mobile_number NOT IN (
            SELECT DISTINCT mobile_number 
            FROM reminders 
            WHERE DATE(sent_at) = DATE('now')
            AND status = 'sent'
        )
        ORDER BY c.due_amount DESC
    ''').fetchall()
    
    db.close()
    return customers

def generate_reminder_message(customer_name, shop_name, due_amount):
    """Generate WhatsApp reminder message with disclaimer"""
    message = f"""🔔 *Payment Reminder - Patt Book*

Dear {customer_name},

You have a pending payment of ₹{due_amount:.2f} at {shop_name}.

This is an automated reminder from Patt Book to help you track your dues.

---
⚠️ *Important Disclaimer:*
• Patt Book does NOT collect payments
• Patt Book is NOT responsible for WhatsApp money requests  
• This message is only a reminder
• This reminder service is FREE for retailers

Please contact the shop directly for payment arrangements.

Thank you for using Patt Book! 📱"""
    
    return message

def send_whatsapp_message(to_number, message):
    """Send WhatsApp message using Facebook Graph API"""
    try:
        headers = {
            'Authorization': f'Bearer {ACCESS_TOKEN}',
            'Content-Type': 'application/json',
        }
        
        data = {
            'messaging_product': 'whatsapp',
            'to': f'91{to_number}',  # Add India country code
            'type': 'template',
            'template': {
                'name': 'payment_reminder',
                'language': {'code': 'en'},
                'components': [
                    {
                        'type': 'body',
                        'parameters': [
                            {'type': 'text', 'text': message}
                        ]
                    }
                ]
            }
        }
        
        # For testing, we'll use text message instead of template
        data = {
            'messaging_product': 'whatsapp',
            'to': f'91{to_number}',
            'type': 'text',
            'text': {
                'body': message
            }
        }
        
        response = requests.post(
            f"{WHATSAPP_API_URL}{PHONE_NUMBER_ID}/messages",
            headers=headers,
            json=data
        )
        
        return response.status_code == 200, response.json()
        
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
        return False, str(e)

def log_reminder(customer_mobile, retailer_mobile, message, status='sent'):
    """Log reminder to database"""
    db = get_db()
    cursor = db.cursor()
    
    # Get retailer and customer IDs
    retailer = db.execute(
        'SELECT id FROM users WHERE mobile_number = ? AND user_type = "retailer"',
        (retailer_mobile,)
    ).fetchone()
    
    customer = db.execute(
        'SELECT id FROM customers WHERE mobile_number = ? AND retailer_id = ?',
        (customer_mobile, retailer['id'] if retailer else None)
    ).fetchone()
    
    if retailer and customer:
        cursor.execute('''
            INSERT INTO reminders (retailer_id, customer_id, message, status)
            VALUES (?, ?, ?, ?)
        ''', (retailer['id'], customer['id'], message, status))
        db.commit()
    
    db.close()

def send_sunday_reminders():
    """Send Sunday reminders to all customers with pending dues"""
    print(f"Starting Sunday reminder process at {datetime.now()}")
    
    customers = get_customers_with_pending_dues()
    print(f"Found {len(customers)} customers with pending dues")
    
    success_count = 0
    failed_count = 0
    
    for customer in customers:
        try:
            # Generate reminder message
            message = generate_reminder_message(
                customer['customer_name'],
                customer['retailer_shop_name'],
                customer['due_amount']
            )
            
            # Send WhatsApp message
            success, response = send_whatsapp_message(
                customer['mobile_number'],
                message
            )
            
            # Log reminder
            log_reminder(
                customer['mobile_number'],
                customer['retailer_mobile'],
                message,
                'sent' if success else 'failed'
            )
            
            if success:
                success_count += 1
                print(f"✅ Reminder sent to {customer['mobile_number']} - ₹{customer['due_amount']}")
            else:
                failed_count += 1
                print(f"❌ Failed to send reminder to {customer['mobile_number']}: {response}")
            
            # Add delay to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            failed_count += 1
            print(f"❌ Error processing customer {customer['mobile_number']}: {e}")
    
    print(f"Sunday reminder process completed:")
    print(f"   Success: {success_count}")
    print(f"   Failed: {failed_count}")
    print(f"   Total: {len(customers)}")

def schedule_sunday_reminders():
    """Schedule Sunday reminders to run at 10:00 AM every Sunday"""
    # Schedule for Sunday at 10:00 AM
    schedule.every().sunday.at("10:00").do(send_sunday_reminders)
    
    print("Sunday reminder scheduler started")
    print("Reminders will be sent every Sunday at 10:00 AM")
    
    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def test_reminder_system():
    """Test the reminder system (for development)"""
    print("Testing Sunday reminder system...")
    
    customers = get_customers_with_pending_dues()
    print(f"Found {len(customers)} customers with pending dues for testing")
    
    if customers:
        # Test with first customer
        customer = customers[0]
        message = generate_reminder_message(
            customer['customer_name'],
            customer['retailer_shop_name'],
            customer['due_amount']
        )
        
        print(f"Sample message for {customer['mobile_number']}:")
        print("=" * 50)
        print(message)
        print("=" * 50)
        
        # Log test reminder
        log_reminder(
            customer['mobile_number'],
            customer['retailer_mobile'],
            message,
            'test'
        )
        
        print("Test reminder logged successfully")
    else:
        print("No customers with pending dues found for testing")

if __name__ == "__main__":
    import os
    
    # Check if running in test mode
    if len(os.argv) > 1 and os.argv[1] == 'test':
        test_reminder_system()
    elif len(os.argv) > 1 and os.argv[1] == 'run-once':
        send_sunday_reminders()
    else:
        # Start the scheduler
        schedule_sunday_reminders()
