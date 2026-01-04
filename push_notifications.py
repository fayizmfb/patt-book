"""
Push Notification System
Handles Firebase Cloud Messaging (FCM) for push notifications
Replaces WhatsApp messaging with free push notifications
"""

import requests
import json
from database import get_db


from firebase_config import FIREBASE_AVAILABLE, verify_firebase_token, get_current_user_id
import firebase_admin
from firebase_admin import messaging

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
    if not FIREBASE_AVAILABLE:
        print("Firebase not available for push notifications")
        return False
        
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

        # Prepare FCM message
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=user['fcm_token'],
            data={k: str(v) for k, v in data.items()} if data else None
        )

        try:
            # Send the message
            response = messaging.send(message)
            print(f"Successfully sent message to user {user_id}: {response}")
            
            # Log the notification
            db.execute(
                'INSERT INTO push_notifications (user_id, title, body, data, status) VALUES (?, ?, ?, ?, ?)',
                (user_id, title, body, json.dumps(data) if data else None, 'sent')
            )
            db.commit()
            return True
        except messaging.ApiCallError as e:
            print(f"FCM Send Error: {e}")
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