"""
Firebase Cloud Messaging (FCM) Service
Handles all FCM push notification operations
"""

import json
import requests
from typing import List, Dict, Any, Optional
from django.conf import settings
import firebase_admin
from firebase_admin import credentials, messaging
import os


class FCMService:
    """Service class for handling Firebase Cloud Messaging operations"""

    _initialized = False

    @classmethod
    def initialize(cls):
        """Initialize Firebase Admin SDK"""
        if cls._initialized:
            return True

        try:
            # Check if credentials file exists
            if settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
                cls._initialized = True
                return True
            else:
                print("Warning: Firebase credentials not found. FCM notifications will not work.")
                return False
        except Exception as e:
            print(f"Error initializing Firebase: {str(e)}")
            return False

    @classmethod
    def send_notification(
        cls,
        device_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
        click_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send push notification to a single device

        Args:
            device_token: FCM device token
            title: Notification title
            body: Notification body
            data: Additional data payload
            image_url: Optional image URL
            click_action: Optional click action

        Returns:
            Dict containing success status and message ID or error
        """
        if not cls._initialized:
            if not cls.initialize():
                return {
                    'success': False,
                    'error': 'FCM not initialized'
                }

        try:
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )

            # Build Android config
            android_config = messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default',
                    click_action=click_action
                )
            )

            # Build APNS (iOS) config
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1
                    )
                )
            )

            # Build message
            message = messaging.Message(
                notification=notification,
                data=data or {},
                token=device_token,
                android=android_config,
                apns=apns_config
            )

            # Send message
            response = messaging.send(message)

            return {
                'success': True,
                'message_id': response
            }

        except messaging.UnregisteredError:
            return {
                'success': False,
                'error': 'Device token is invalid or unregistered',
                'error_code': 'UNREGISTERED'
            }
        except messaging.SenderIdMismatchError:
            return {
                'success': False,
                'error': 'Sender ID mismatch',
                'error_code': 'SENDER_ID_MISMATCH'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @classmethod
    def send_multicast(
        cls,
        device_tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send push notification to multiple devices

        Args:
            device_tokens: List of FCM device tokens
            title: Notification title
            body: Notification body
            data: Additional data payload
            image_url: Optional image URL

        Returns:
            Dict containing success count, failure count, and responses
        """
        if not cls._initialized:
            if not cls.initialize():
                return {
                    'success': False,
                    'error': 'FCM not initialized'
                }

        try:
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )

            # Build multicast message
            message = messaging.MulticastMessage(
                notification=notification,
                data=data or {},
                tokens=device_tokens,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(sound='default')
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound='default', badge=1)
                    )
                )
            )

            # Send multicast
            response = messaging.send_multicast(message)

            # Collect invalid tokens
            invalid_tokens = []
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        invalid_tokens.append(device_tokens[idx])

            return {
                'success': True,
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'invalid_tokens': invalid_tokens
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @classmethod
    def send_to_topic(
        cls,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification to a topic

        Args:
            topic: Topic name (e.g., 'all_users', 'providers')
            title: Notification title
            body: Notification body
            data: Additional data payload
            image_url: Optional image URL

        Returns:
            Dict containing success status and message ID or error
        """
        if not cls._initialized:
            if not cls.initialize():
                return {
                    'success': False,
                    'error': 'FCM not initialized'
                }

        try:
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )

            message = messaging.Message(
                notification=notification,
                data=data or {},
                topic=topic
            )

            response = messaging.send(message)

            return {
                'success': True,
                'message_id': response
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @classmethod
    def subscribe_to_topic(cls, tokens: List[str], topic: str) -> Dict[str, Any]:
        """
        Subscribe device tokens to a topic

        Args:
            tokens: List of device tokens
            topic: Topic name

        Returns:
            Dict containing success and failure counts
        """
        if not cls._initialized:
            if not cls.initialize():
                return {
                    'success': False,
                    'error': 'FCM not initialized'
                }

        try:
            response = messaging.subscribe_to_topic(tokens, topic)

            return {
                'success': True,
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'errors': response.errors
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @classmethod
    def unsubscribe_from_topic(cls, tokens: List[str], topic: str) -> Dict[str, Any]:
        """
        Unsubscribe device tokens from a topic

        Args:
            tokens: List of device tokens
            topic: Topic name

        Returns:
            Dict containing success and failure counts
        """
        if not cls._initialized:
            if not cls.initialize():
                return {
                    'success': False,
                    'error': 'FCM not initialized'
                }

        try:
            response = messaging.unsubscribe_from_topic(tokens, topic)

            return {
                'success': True,
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'errors': response.errors
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @classmethod
    def send_data_message(
        cls,
        device_token: str,
        data: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Send data-only message (no notification, handled by app)

        Args:
            device_token: FCM device token
            data: Data payload

        Returns:
            Dict containing success status and message ID or error
        """
        if not cls._initialized:
            if not cls.initialize():
                return {
                    'success': False,
                    'error': 'FCM not initialized'
                }

        try:
            message = messaging.Message(
                data=data,
                token=device_token,
                android=messaging.AndroidConfig(priority='high')
            )

            response = messaging.send(message)

            return {
                'success': True,
                'message_id': response
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Helper functions for common notification types
def send_booking_notification(user_devices, booking_id: int, title: str, body: str):
    """Send booking-related notification"""
    device_tokens = [device.device_token for device in user_devices if device.is_active]

    if not device_tokens:
        return {'success': False, 'error': 'No active devices'}

    data = {
        'type': 'booking',
        'booking_id': str(booking_id),
        'click_action': 'FLUTTER_NOTIFICATION_CLICK'
    }

    return FCMService.send_multicast(
        device_tokens=device_tokens,
        title=title,
        body=body,
        data=data
    )


def send_message_notification(user_devices, conversation_id: int, sender_name: str, message: str):
    """Send new message notification"""
    device_tokens = [device.device_token for device in user_devices if device.is_active]

    if not device_tokens:
        return {'success': False, 'error': 'No active devices'}

    data = {
        'type': 'message',
        'conversation_id': str(conversation_id),
        'click_action': 'FLUTTER_NOTIFICATION_CLICK'
    }

    return FCMService.send_multicast(
        device_tokens=device_tokens,
        title=f'New message from {sender_name}',
        body=message[:100],
        data=data
    )


def send_payment_notification(user_devices, payment_id: int, title: str, body: str):
    """Send payment-related notification"""
    device_tokens = [device.device_token for device in user_devices if device.is_active]

    if not device_tokens:
        return {'success': False, 'error': 'No active devices'}

    data = {
        'type': 'payment',
        'payment_id': str(payment_id),
        'click_action': 'FLUTTER_NOTIFICATION_CLICK'
    }

    return FCMService.send_multicast(
        device_tokens=device_tokens,
        title=title,
        body=body,
        data=data
    )
