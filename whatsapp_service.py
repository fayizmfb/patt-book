"""
Patt Book - WhatsApp OTP Service
WhatsApp Cloud API Integration for Retailer Authentication & Notifications
"""

import requests
import random
import json
from datetime import datetime, timedelta
from database_retailer import get_db, hash_otp, cleanup_expired_otps
import os

# WhatsApp Cloud API Configuration
WHATSAPP_API_VERSION = 'v18.0'
WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
WHATSAPP_ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')
WHATSAPP_API_URL = f'https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages'

# Test mode for development
TEST_MODE = os.environ.get('TEST_MODE', 'true').lower() == 'true'

def generate_otp():
    """Generate 6-digit OTP"""
    return str(random.randint(100000, 999999))

def send_whatsapp_otp(phone_number, otp):
    """Send OTP via WhatsApp"""
    try:
        # Clean phone number (remove +, spaces, etc.)
        clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        
        if TEST_MODE or not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            print(f"TEST MODE - WhatsApp OTP would be sent to {clean_phone}: {otp}")
            return True
        
        # WhatsApp Cloud API request
        headers = {
            'Authorization': f'Bearer {WHATSAPP_ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "template",
            "template": {
                "name": "LOGIN_OTP",
                "language": {
                    "code": "en_US"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {
                                "type": "text",
                                "text": otp
                            },
                            {
                                "type": "text", 
                                "text": "5"
                            }
                        ]
                    }
                ]
            }
        }
        
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
        
        if response.status_code == 200:
            print(f"WhatsApp OTP sent successfully to {clean_phone}")
            return True
        else:
            print(f"WhatsApp OTP failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending WhatsApp OTP: {e}")
        return False

def store_otp(phone, otp):
    """Store hashed OTP in database"""
    db = get_db()
    try:
        # Clean up expired OTPs first
        cleanup_expired_otps()
        
        # Delete any existing OTP for this phone
        db.execute('DELETE FROM otp_requests WHERE phone = ?', (phone,))
        
        # Store new OTP
        expires_at = datetime.now() + timedelta(minutes=5)
        otp_hash = hash_otp(otp)
        
        db.execute(
            'INSERT INTO otp_requests (phone, otp_hash, expires_at) VALUES (?, ?, ?)',
            (phone, otp_hash, expires_at)
        )
        
        db.commit()
        return True
    except Exception as e:
        print(f"Error storing OTP: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def verify_otp(phone, otp):
    """Verify OTP and return success/failure"""
    db = get_db()
    try:
        # Get OTP record
        result = db.execute(
            'SELECT otp_hash, expires_at, attempts FROM otp_requests WHERE phone = ?',
            (phone,)
        ).fetchone()
        
        if not result:
            return {'success': False, 'message': 'No OTP found for this phone number'}
        
        # Check if expired
        if datetime.now() > datetime.fromisoformat(result['expires_at']):
            db.execute('DELETE FROM otp_requests WHERE phone = ?', (phone,))
            db.commit()
            return {'success': False, 'message': 'OTP expired. Please request a new one.'}
        
        # Check attempts
        if result['attempts'] >= 3:
            db.execute('DELETE FROM otp_requests WHERE phone = ?', (phone,))
            db.commit()
            return {'success': False, 'message': 'Too many attempts. Please request a new OTP.'}
        
        # Verify OTP
        otp_hash = hash_otp(otp)
        if otp_hash == result['otp_hash']:
            # OTP verified - delete it
            db.execute('DELETE FROM otp_requests WHERE phone = ?', (phone,))
            db.commit()
            return {'success': True, 'message': 'OTP verified successfully'}
        else:
            # Increment attempts
            db.execute(
                'UPDATE otp_requests SET attempts = attempts + 1 WHERE phone = ?',
                (phone,)
            )
            db.commit()
            remaining_attempts = 3 - (result['attempts'] + 1)
            return {
                'success': False, 
                'message': f'Invalid OTP. {remaining_attempts} attempts remaining.'
            }
            
    except Exception as e:
        print(f"Error verifying OTP: {e}")
        return {'success': False, 'message': 'Verification failed'}
    finally:
        db.close()

def send_whatsapp_notification(phone_number, template_name, parameters):
    """Send WhatsApp notification (async)"""
    try:
        # Clean phone number
        clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        
        if TEST_MODE or not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            print(f"TEST MODE - WhatsApp notification would be sent to {clean_phone}")
            print(f"Template: {template_name}")
            print(f"Parameters: {parameters}")
            return True
        
        # WhatsApp Cloud API request
        headers = {
            'Authorization': f'Bearer {WHATSAPP_ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": "en_US"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": parameters
                    }
                ]
            }
        }
        
        # Send asynchronously (non-blocking)
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            print(f"WhatsApp notification sent successfully to {clean_phone}")
            return True
        else:
            print(f"WhatsApp notification failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending WhatsApp notification: {e}")
        return False

def send_credit_added_notification(customer_name, shop_name, amount, total_due, phone_number):
    """Send credit added notification"""
    parameters = [
        {"type": "text", "text": customer_name},
        {"type": "text", "text": shop_name},
        {"type": "text", "text": str(amount)},
        {"type": "text", "text": str(total_due)}
    ]
    
    return send_whatsapp_notification(phone_number, "CREDIT_ADDED", parameters)

def send_payment_recorded_notification(customer_name, shop_name, amount, balance, phone_number):
    """Send payment recorded notification"""
    parameters = [
        {"type": "text", "text": customer_name},
        {"type": "text", "text": str(amount)},
        {"type": "text", "text": shop_name},
        {"type": "text", "text": str(balance)}
    ]
    
    return send_whatsapp_notification(phone_number, "PAYMENT_RECORDED", parameters)
