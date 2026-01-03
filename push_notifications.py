"""
Push Notification System
Handles Firebase Cloud Messaging (FCM) for push notifications
Replaces WhatsApp messaging with free push notifications
"""

import requests
import json
from database import get_db


def get_fcm_server_key():
    """Get FCM server key from settings"""
    db = get_db()
    try:
        result = db.execute(
            'SELECT value FROM system_settings WHERE key = ?',
            ('fcm_server_key',)
        ).fetchone()
        return result['value'] if result else None
    except:
        return None
    finally:
        db.close()


def send_push_notification(user_id, title, body, data=None):
    """
    Send push notification to a user via FCM

    Args:
        user_id: User ID to send notification to
        title: Notification title
        body: Notification body
        data: Additional data payload (dict)

    Returns:
        bool: True if sent successfully, False otherwise
    """
    db = get_db()
    try:
        # Get user's FCM token
        user = db.execute(
            'SELECT fcm_token FROM users WHERE id = ? AND is_active = 1',
            (user_id,)
        ).fetchone()

        if not user or not user['fcm_token']:
            print(f"No FCM token found for user {user_id}")
            return False

        fcm_server_key = get_fcm_server_key()
        if not fcm_server_key:
            print("FCM server key not configured")
            return False

        # Prepare FCM payload
        payload = {
            "to": user['fcm_token'],
            "notification": {
                "title": title,
                "body": body,
                "sound": "default"
            }
        }

        if data:
            payload["data"] = {k: str(v) for k, v in data.items()}  # FCM requires string values

        headers = {
            'Authorization': f'key={fcm_server_key}',
            'Content-Type': 'application/json'
        }

        response = requests.post(
            'https://fcm.googleapis.com/fcm/send',
            json=payload,
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            # Log the notification
            db.execute(
                'INSERT INTO push_notifications (user_id, title, body, data, status) VALUES (?, ?, ?, ?, ?)',
                (user_id, title, body, json.dumps(data) if data else None, 'sent')
            )
            db.commit()
            print(f"Push notification sent to user {user_id}")
            return True
        else:
            print(f"Failed to send push notification: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"Exception sending push notification: {str(e)}")
        return False
    finally:
        db.close()


def prepare_credit_notification(retailer_name, amount, total_outstanding):
    """
    Prepare credit entry notification

    Args:
        retailer_name: Name of the retailer/store
        amount: Credit amount added
        total_outstanding: Total outstanding balance

    Returns:
        tuple: (title, body) for the notification
    """
    title = f"{retailer_name}"
    body = f"Credit added: ₹{amount:.2f}\nTotal outstanding: ₹{total_outstanding:.2f}"

    return title, body


def prepare_payment_request_notification(customer_name, amount):
    """
    Prepare payment request notification for retailer

    Args:
        customer_name: Name of the customer
        amount: Payment amount requested

    Returns:
        tuple: (title, body) for the notification
    """
    title = "Payment Request"
    body = f"{customer_name} submitted payment: ₹{amount:.2f}"

    return title, body


def prepare_payment_confirmed_notification(retailer_name, amount):
    """
    Prepare payment confirmation notification for customer

    Args:
        retailer_name: Name of the retailer/store
        amount: Payment amount confirmed

    Returns:
        tuple: (title, body) for the notification
    """
    title = f"{retailer_name}"
    body = f"Payment confirmed: ₹{amount:.2f}"

    return title, body


def update_user_fcm_token(user_id, fcm_token):
    """
    Update user's FCM token for push notifications

    Args:
        user_id: User ID
        fcm_token: Firebase Cloud Messaging token

    Returns:
        bool: True if updated successfully
    """
    db = get_db()
    try:
        db.execute(
            'UPDATE users SET fcm_token = ? WHERE id = ?',
            (fcm_token, user_id)
        )
        db.commit()
        return True
    except Exception as e:
        print(f"Error updating FCM token: {str(e)}")
        return False
    finally:
        db.close()