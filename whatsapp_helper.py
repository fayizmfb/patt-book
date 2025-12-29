"""
WhatsApp Business Platform Integration
Handles sending WhatsApp messages via WhatsApp Business API
"""

import requests
from database import get_db


def get_setting(key, default=''):
    """Helper function to get a setting value from database"""
    db = get_db()
    try:
        result = db.execute(
            'SELECT value FROM settings WHERE key = ?',
            (key,)
        ).fetchone()
        return result['value'] if result else default
    except:
        return default
    finally:
        db.close()


def send_whatsapp_message(phone_number, message_body):
    """
    Send WhatsApp message using WhatsApp Business Platform API
    
    This function uses a generic WhatsApp Business API endpoint.
    You'll need to configure your API credentials in settings.
    
    Args:
        phone_number: Customer phone number (with country code, e.g., +1234567890)
        message_body: The message text to send
    
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    # Get WhatsApp API configuration from settings
    api_url = get_setting('whatsapp_api_url', '')
    api_token = get_setting('whatsapp_api_token', '')
    phone_id = get_setting('whatsapp_phone_id', '')
    
    # If API credentials not configured, skip sending (for development/testing)
    if not api_url or not api_token or not phone_id:
        print(f"WhatsApp API not configured. Would send to {phone_number}: {message_body[:50]}...")
        return False
    
    # Clean phone number (remove spaces, dashes, etc.)
    phone_number = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    
    try:
        # Prepare request headers
        headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        
        # Prepare request payload (WhatsApp Business API format)
        payload = {
            'messaging_product': 'whatsapp',
            'to': phone_number,
            'type': 'text',
            'text': {
                'body': message_body
            }
        }
        
        # Send message via WhatsApp Business API
        # Note: Endpoint format may vary based on your WhatsApp Business provider
        endpoint = f"{api_url}/v17.0/{phone_id}/messages"
        
        response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"WhatsApp message sent successfully to {phone_number}")
            return True
        else:
            print(f"Error sending WhatsApp message: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception while sending WhatsApp message: {str(e)}")
        return False


def prepare_welcome_message(customer_name, store_name):
    """
    Prepare welcome message when a new customer is added
    
    Args:
        customer_name: Name of the newly added customer
        store_name: Name of the store from settings
    
    Returns:
        str: Formatted welcome message
    """
    message = f"""Hello {customer_name},

Welcome! You have been added as a customer by {store_name}.

This is Patt Book - we help {store_name} track credit accounts and send payment reminders.

IMPORTANT:
• Patt Book does NOT collect payments
• Do NOT make payments through any links or apps
• Always verify payment requests directly with {store_name} to avoid fraud

For any questions, please contact {store_name} directly.

Thank you!"""
    
    return message


def prepare_credit_confirmation_message(customer_name, store_name, amount, due_date):
    """
    Prepare immediate confirmation message when credit is granted
    
    Args:
        customer_name: Name of the customer
        store_name: Name of the store from settings
        amount: Credit amount granted
        due_date: Due date for the payment (string format: 'YYYY-MM-DD' or date object)
    
    Returns:
        str: Formatted credit confirmation message
    """
    # Format due date as string if it's a date object
    if hasattr(due_date, 'strftime'):
        due_date_str = due_date.strftime('%Y-%m-%d')
    else:
        due_date_str = str(due_date)
    
    message = f"""Hello {customer_name},

Thank you for your purchase at {store_name}!

Credit Details:
• Store: {store_name}
• Credit Amount: {amount:.2f}
• Due Date: {due_date_str}

Please keep this information for your records.

IMPORTANT:
• Patt Book does NOT collect payments
• Do NOT make payments through any links or apps
• Always verify payment requests directly with {store_name} to avoid fraud

For any questions, please contact {store_name} directly.

Thank you!"""
    
    return message


def prepare_pre_due_reminder_message(customer_name, store_name, outstanding_balance, due_date, days_until_due):
    """
    Prepare pre-due reminder message sent before payment is due
    
    Args:
        customer_name: Name of the customer
        store_name: Name of the store from settings
        outstanding_balance: Current outstanding balance for the customer
        due_date: Due date for the payment (date object)
        days_until_due: Number of days until due date
    
    Returns:
        str: Formatted pre-due reminder message
    """
    # Format due date as string
    if hasattr(due_date, 'strftime'):
        due_date_str = due_date.strftime('%Y-%m-%d')
    else:
        due_date_str = str(due_date)
    
    # Format the days information based on whether it's overdue or not
    if days_until_due < 0:
        days_info = f"Days Overdue: {abs(days_until_due)}"
        urgency_text = "Your payment is overdue. Please settle your account as soon as possible."
    elif days_until_due == 0:
        days_info = "Due Date: Today"
        urgency_text = "Your payment is due today. Please settle your account."
    else:
        days_info = f"Days Until Due: {days_until_due}"
        urgency_text = "Please plan to settle your account by the due date."
    
    message = f"""Hello {customer_name},

This is a friendly reminder from {store_name}.

Payment Reminder:
• Store: {store_name}
• Outstanding Balance: {outstanding_balance:.2f}
• Due Date: {due_date_str}
• {days_info}

{urgency_text}

IMPORTANT:
• Patt Book does NOT collect payments
• Do NOT make payments through any links or apps
• Always verify payment requests directly with {store_name} to avoid fraud

For any questions, please contact {store_name} directly.

Thank you!"""
    
    return message


def send_pre_due_reminders():
    """
    Check for credits that need pre-due reminders and send them
    
    This function should be called periodically (e.g., daily) to send
    reminders before due dates.
    
    Reminder timing: reminder_date = due_date - (due_days / 2)
    """
    from database import get_db
    from datetime import datetime, timedelta
    
    db = get_db()
    today = datetime.now().date()
    
    try:
        # Find credits where reminder should be sent today
        # reminder_date = due_date - (due_days / 2)
        credits_needing_reminder = db.execute("""
            SELECT 
                c.id as credit_id,
                c.customer_id,
                c.amount,
                c.due_date,
                c.due_days,
                cust.name as customer_name,
                cust.phone,
                (c.due_date - (c.due_days / 2)) as reminder_date
            FROM credits c
            JOIN customers cust ON c.customer_id = cust.id
            WHERE c.due_date > ?
            AND (c.due_date - (c.due_days / 2)) = ?
            AND cust.phone IS NOT NULL
            AND cust.phone != ''
        """, (today, today)).fetchall()
        
        # Get store name
        store_setting = db.execute(
            "SELECT value FROM settings WHERE key = 'store_name'"
        ).fetchone()
        store_name = store_setting['value'] if store_setting and store_setting['value'] else 'Your Store'
        
        reminders_sent = 0
        
        for credit in credits_needing_reminder:
            try:
                # Calculate current outstanding balance for this customer
                total_credits = db.execute(
                    'SELECT COALESCE(SUM(amount), 0) FROM credits WHERE customer_id = ?',
                    (credit['customer_id'],)
                ).fetchone()[0]
                
                total_payments = db.execute(
                    'SELECT COALESCE(SUM(amount), 0) FROM payments WHERE customer_id = ?',
                    (credit['customer_id'],)
                ).fetchone()[0]
                
                outstanding_balance = max(0, total_credits - total_payments)
                
                # Only send if there's still an outstanding balance
                if outstanding_balance > 0:
                    # Calculate days until due
                    days_until_due = (credit['due_date'] - today).days
                    
                    # Prepare and send pre-due reminder
                    reminder_msg = prepare_pre_due_reminder_message(
                        credit['customer_name'],
                        store_name,
                        outstanding_balance,
                        credit['due_date'],
                        days_until_due
                    )
                    
                    if send_whatsapp_message(credit['phone'], reminder_msg):
                        reminders_sent += 1
                        print(f"Pre-due reminder sent to {credit['customer_name']} for credit ID {credit['credit_id']}")
            
            except Exception as e:
                print(f"Error sending pre-due reminder for credit ID {credit['credit_id']}: {str(e)}")
        
        print(f"Pre-due reminder check completed. Sent {reminders_sent} reminders.")
        return reminders_sent
        
    except Exception as e:
        print(f"Error in send_pre_due_reminders: {str(e)}")
        return 0
    finally:
        db.close()

