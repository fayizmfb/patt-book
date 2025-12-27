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


def prepare_reminder_message(customer_name, store_name, outstanding_amount, due_date, days_overdue=0):
    """
    Prepare payment reminder message when due date arrives or has passed
    
    Args:
        customer_name: Name of the customer
        store_name: Name of the store from settings
        outstanding_amount: Outstanding balance amount
        due_date: Due date for the payment (string format: 'YYYY-MM-DD' or date object)
        days_overdue: Number of days since due date (0 if due today, >0 if overdue)
    
    Returns:
        str: Formatted reminder message
    """
    # Format due date as string if it's a date object
    if hasattr(due_date, 'strftime'):
        due_date_str = due_date.strftime('%Y-%m-%d')
    else:
        due_date_str = str(due_date)
    
    # Build message with or without days overdue
    if days_overdue > 0:
        days_info = f"\n• Days Overdue: {days_overdue} days"
    else:
        days_info = ""
    
    message = f"""Hello {customer_name},

This is a payment reminder from Patt Book on behalf of {store_name}.

Payment Details:
• Store: {store_name}
• Outstanding Amount: {outstanding_amount:.2f}
• Due Date: {due_date_str}{days_info}

Please settle your outstanding balance with {store_name}.

IMPORTANT:
• Patt Book does NOT collect payments
• Do NOT make payments through any links or apps sent via WhatsApp
• Always verify and make payments directly with {store_name} to avoid fraud
• This is only a reminder service - Patt Book cannot process payments

For payment arrangements, please contact {store_name} directly.

Thank you!"""
    
    return message

