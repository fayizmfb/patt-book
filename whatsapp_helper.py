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


def prepare_credit_entry_message(customer_name, store_name, current_amount, total_outstanding):
    """
    Prepare credit entry notification message

    Args:
        customer_name: Name of the customer
        store_name: Name of the store from settings
        current_amount: The amount of the current credit entry
        total_outstanding: Total outstanding balance after this entry

    Returns:
        str: Formatted credit entry message
    """
    message = f"""Hello {customer_name},

Thank you for your purchase at {store_name}!

Today's Purchase: ₹{current_amount:.2f}
Total Outstanding Balance: ₹{total_outstanding:.2f}

Please keep this information for your records.

Regards,
{store_name} - Patt Book"""

    return message


def prepare_manual_reminder_message(customer_name, store_name, total_outstanding):
    """
    Prepare manual reminder message for outstanding balance

    Args:
        customer_name: Name of the customer
        store_name: Name of the store from settings
        total_outstanding: Current total outstanding balance

    Returns:
        str: Formatted manual reminder message
    """
    message = f"""Hello {customer_name},

This is a friendly reminder from {store_name}.

Your current outstanding balance is: ₹{total_outstanding:.2f}

Please settle your account at your earliest convenience.

Regards,
{store_name} - Patt Book"""

    return message

