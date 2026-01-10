"""
Email OTP Authentication System
Patt Book - Secure Authentication with Email OTP
"""

import smtplib
import random
import jwt
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import get_db, hash_otp
import os

# Email configuration
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USER = os.environ.get('EMAIL_USER', '')
EMAIL_PASS = os.environ.get('EMAIL_PASS', '')

# JWT configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')
JWT_EXPIRY = timedelta(hours=24)

def generate_otp():
    """Generate 6-digit OTP"""
    return str(random.randint(100000, 999999))

def send_email_otp(to_email, otp):
    """Send OTP via email"""
    try:
        # Check if email credentials are configured
        if not EMAIL_USER or not EMAIL_PASS or EMAIL_USER == 'your-email@gmail.com':
            print(f"TEST MODE - OTP would be sent to {to_email}: {otp}")
            return True
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = 'Patt Book - Email Verification OTP'
        
        body = f"""
        <html>
        <body>
            <h2>Patt Book - Email Verification</h2>
            <p>Your OTP code is: <strong>{otp}</strong></p>
            <p>This OTP will expire in 5 minutes.</p>
            <p>If you didn't request this OTP, please ignore this email.</p>
            <br>
            <p>Thanks,<br>Patt Book Team</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, to_email, text)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def store_otp(email, otp):
    """Store hashed OTP in database"""
    db = get_db()
    try:
        # Delete any existing OTP for this email
        db.execute('DELETE FROM email_otps WHERE email = ?', (email,))
        
        # Store new OTP
        expires_at = datetime.now() + timedelta(minutes=5)
        otp_hash = hash_otp(otp)
        
        db.execute(
            'INSERT INTO email_otps (email, otp_hash, expires_at) VALUES (?, ?, ?)',
            (email, otp_hash, expires_at)
        )
        
        db.commit()
        return True
    except Exception as e:
        print(f"Error storing OTP: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def verify_otp(email, otp):
    """Verify OTP and return success/failure"""
    db = get_db()
    try:
        # Get OTP record
        result = db.execute(
            'SELECT otp_hash, expires_at, attempts FROM email_otps WHERE email = ?',
            (email,)
        ).fetchone()
        
        if not result:
            return {'success': False, 'message': 'No OTP found for this email'}
        
        # Check if expired
        if datetime.now() > datetime.fromisoformat(result['expires_at']):
            db.execute('DELETE FROM email_otps WHERE email = ?', (email,))
            db.commit()
            return {'success': False, 'message': 'OTP expired. Please request a new one.'}
        
        # Check attempts
        if result['attempts'] >= 3:
            db.execute('DELETE FROM email_otps WHERE email = ?', (email,))
            db.commit()
            return {'success': False, 'message': 'Too many attempts. Please request a new OTP.'}
        
        # Verify OTP
        otp_hash = hash_otp(otp)
        if otp_hash == result['otp_hash']:
            # OTP verified - delete it
            db.execute('DELETE FROM email_otps WHERE email = ?', (email,))
            db.commit()
            return {'success': True, 'message': 'OTP verified successfully'}
        else:
            # Increment attempts
            db.execute(
                'UPDATE email_otps SET attempts = attempts + 1 WHERE email = ?',
                (email,)
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

def generate_jwt_token(user_data):
    """Generate JWT token for authenticated user"""
    payload = {
        'user_id': user_data['phone'],
        'email': user_data['email'],
        'user_type': user_data['user_type'],
        'exp': datetime.now() + JWT_EXPIRY
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    return token

def verify_jwt_token(token):
    """Verify JWT token and return user data"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def check_email_exists(email):
    """Check if email already exists"""
    db = get_db()
    try:
        # Check in retailers table
        result = db.execute('SELECT email FROM retailers WHERE email = ?', (email,)).fetchone()
        if result:
            return True
        
        # Check in customers table
        result = db.execute('SELECT email FROM customers WHERE email = ?', (email,)).fetchone()
        return result is not None
    except Exception as e:
        print(f"Error checking email: {e}")
        return False
    finally:
        db.close()

def check_phone_exists(phone):
    """Check if phone already exists"""
    db = get_db()
    try:
        # Check in retailers table
        result = db.execute('SELECT retailer_phone FROM retailers WHERE retailer_phone = ?', (phone,)).fetchone()
        if result:
            return True
        
        # Check in customers table
        result = db.execute('SELECT phone FROM customers WHERE phone = ?', (phone,)).fetchone()
        return result is not None
    except Exception as e:
        print(f"Error checking phone: {e}")
        return False
    finally:
        db.close()

def check_email_phone_exists(email, phone, user_type):
    """Check if email + phone combination exists"""
    db = get_db()
    try:
        if user_type == 'retailer':
            result = db.execute(
                'SELECT * FROM retailers WHERE email = ? AND retailer_phone = ?',
                (email, phone)
            ).fetchone()
        else:
            result = db.execute(
                'SELECT * FROM customers WHERE email = ? AND phone = ?',
                (email, phone)
            ).fetchone()
        
        return result is not None
    except Exception as e:
        print(f"Error checking email/phone: {e}")
        return False
    finally:
        db.close()
