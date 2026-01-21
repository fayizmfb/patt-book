"""
PIN Authentication Service for Patt Book v1
Secure phone + PIN authentication without OTP dependency
"""

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import json

# PIN attempt tracking (in production, use Redis or database)
pin_attempts = {}

def hash_pin(pin):
    """Hash PIN securely using werkzeug"""
    return generate_password_hash(pin)

def verify_pin(stored_hash, entered_pin):
    """Verify PIN against stored hash"""
    return check_password_hash(stored_hash, entered_pin)

def is_pin_locked(phone):
    """Check if PIN attempts are locked for this phone"""
    if phone not in pin_attempts:
        return False, None
    
    attempts = pin_attempts[phone]
    if attempts['count'] >= 5:
        lock_until = attempts['locked_until']
        if lock_until and datetime.utcnow() < lock_until:
            return True, lock_until
        else:
            # Lock expired, reset attempts
            del pin_attempts[phone]
            return False, None
    
    return False, None

def record_pin_attempt(phone, success):
    """Record PIN attempt for rate limiting"""
    if phone not in pin_attempts:
        pin_attempts[phone] = {'count': 0, 'locked_until': None}
    
    if success:
        # Reset on successful login
        del pin_attempts[phone]
    else:
        # Increment failed attempts
        pin_attempts[phone]['count'] += 1
        
        # Lock after 5 failed attempts for 15 minutes
        if pin_attempts[phone]['count'] >= 5:
            pin_attempts[phone]['locked_until'] = datetime.utcnow() + timedelta(minutes=15)

def validate_phone_number(phone):
    """Validate phone number format"""
    if not phone:
        return False, "Phone number is required"
    
    phone = phone.strip()
    
    # Remove any non-digit characters
    phone = ''.join(filter(str.isdigit, phone))
    
    if len(phone) != 10:
        return False, "Valid 10-digit phone number required"
    
    if not phone.isdigit():
        return False, "Phone number must contain only digits"
    
    return True, phone

def validate_pin(pin):
    """Validate PIN format"""
    if not pin:
        return False, "PIN is required"
    
    pin = pin.strip()
    
    if len(pin) < 4 or len(pin) > 6:
        return False, "PIN must be 4-6 digits"
    
    if not pin.isdigit():
        return False, "PIN must contain only digits"
    
    return True, pin

def get_pin_attempts_remaining(phone):
    """Get remaining PIN attempts before lock"""
    if phone not in pin_attempts:
        return 5
    
    return max(0, 5 - pin_attempts[phone]['count'])

def get_lock_time_remaining(phone):
    """Get remaining lock time in minutes"""
    locked, lock_until = is_pin_locked(phone)
    if not locked:
        return 0
    
    remaining = lock_until - datetime.utcnow()
    return max(0, int(remaining.total_seconds() / 60))

def clear_pin_attempts(phone):
    """Clear PIN attempts (for admin use)"""
    if phone in pin_attempts:
        del pin_attempts[phone]
