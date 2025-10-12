"""
FCM (Firebase Cloud Messaging) Views
All FCM-related API endpoints for push notifications
"""

from rest_framework import status, permissions, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction
from .models import FCMDevice, Notification
from .serializers import FCMDeviceSerializer
from .fcm_service import FCMService
from django.contrib.auth import get_user_model

User = get_user_model()


class FCMDeviceRegisterView(generics.CreateAPIView):
    """
    Register a new FCM device token for push notifications

    POST /api/services/fcm/register/
    {
        "device_token": "fcm_token_here",
        "device_type": "android",  # or "ios", "web"
        "device_name": "Samsung Galaxy S21"  # optional
    }
    """
    serializer_class = FCMDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FCMDeviceListView(generics.ListAPIView):
    """
    List all registered devices for the authenticated user

    GET /api/services/fcm/devices/
    """
    serializer_class = FCMDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FCMDevice.objects.filter(user=self.request.user)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_device_token(request, device_id):
    """
    Update an existing device token

    PUT /api/services/fcm/devices/<device_id>/
    {
        "device_token": "new_fcm_token",
        "device_name": "New Device Name"  # optional
    }
    """
    try:
        device = FCMDevice.objects.get(id=device_id, user=request.user)

        device_token = request.data.get('device_token')
        device_name = request.data.get('device_name')

        if device_token:
            device.device_token = device_token
        if device_name:
            device.device_name = device_name

        device.save()

        serializer = FCMDeviceSerializer(device)
        return Response(serializer.data)

    except FCMDevice.DoesNotExist:
        return Response(
            {'error': 'Device not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def unregister_device(request, device_id):
    """
    Unregister (delete) a device

    DELETE /api/services/fcm/devices/<device_id>/
    """
    try:
        device = FCMDevice.objects.get(id=device_id, user=request.user)
        device.delete()

        return Response(
            {'message': 'Device unregistered successfully'},
            status=status.HTTP_200_OK
        )

    except FCMDevice.DoesNotExist:
        return Response(
            {'error': 'Device not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def toggle_device_status(request, device_id):
    """
    Enable or disable push notifications for a specific device

    PUT /api/services/fcm/devices/<device_id>/toggle/
    {
        "is_active": false
    }
    """
    try:
        device = FCMDevice.objects.get(id=device_id, user=request.user)
        is_active = request.data.get('is_active')

        if is_active is not None:
            device.is_active = is_active
            device.save()

        serializer = FCMDeviceSerializer(device)
        return Response(serializer.data)

    except FCMDevice.DoesNotExist:
        return Response(
            {'error': 'Device not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_test_notification(request):
    """
    Send a test notification to the user's devices

    POST /api/services/fcm/test/
    {
        "title": "Test Notification",
        "body": "This is a test notification",
        "device_id": 123  # optional, sends to specific device
    }
    """
    title = request.data.get('title', 'Test Notification')
    body = request.data.get('body', 'This is a test notification from SkillBuddy')
    device_id = request.data.get('device_id')

    try:
        if device_id:
            # Send to specific device
            device = FCMDevice.objects.get(id=device_id, user=request.user, is_active=True)
            result = FCMService.send_notification(
                device_token=device.device_token,
                title=title,
                body=body,
                data={'type': 'test'}
            )
        else:
            # Send to all user's devices
            devices = FCMDevice.objects.filter(user=request.user, is_active=True)
            device_tokens = [device.device_token for device in devices]

            if not device_tokens:
                return Response(
                    {'error': 'No active devices found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            result = FCMService.send_multicast(
                device_tokens=device_tokens,
                title=title,
                body=body,
                data={'type': 'test'}
            )

        if result['success']:
            return Response({
                'message': 'Test notification sent successfully',
                'result': result
            })
        else:
            return Response(
                {'error': result.get('error', 'Failed to send notification')},
                status=status.HTTP_400_BAD_REQUEST
            )

    except FCMDevice.DoesNotExist:
        return Response(
            {'error': 'Device not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_notification_to_user(request):
    """
    Send a notification to a specific user (admin/provider use)

    POST /api/services/fcm/send/
    {
        "user_id": 123,
        "title": "New Booking",
        "body": "You have a new booking request",
        "data": {"booking_id": "456"},  # optional
        "save_notification": true  # optional, saves to database
    }
    """
    user_id = request.data.get('user_id')
    title = request.data.get('title')
    body = request.data.get('body')
    data = request.data.get('data', {})
    save_notification = request.data.get('save_notification', True)

    if not all([user_id, title, body]):
        return Response(
            {'error': 'user_id, title, and body are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(id=user_id)
        devices = FCMDevice.objects.filter(user=user, is_active=True)
        device_tokens = [device.device_token for device in devices]

        if not device_tokens:
            return Response(
                {'error': 'No active devices found for user'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Send FCM notification
        result = FCMService.send_multicast(
            device_tokens=device_tokens,
            title=title,
            body=body,
            data=data
        )

        # Save to database if requested
        if save_notification:
            notification_type = data.get('type', 'system')
            Notification.objects.create(
                user=user,
                notification_type=notification_type,
                title=title,
                message=body
            )

        # Handle invalid tokens
        if result.get('invalid_tokens'):
            FCMDevice.objects.filter(
                device_token__in=result['invalid_tokens']
            ).update(is_active=False)

        return Response({
            'message': 'Notification sent successfully',
            'success_count': result.get('success_count', 0),
            'failure_count': result.get('failure_count', 0)
        })

    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_topic_notification(request):
    """
    Send notification to a topic (admin only)

    POST /api/services/fcm/topic/send/
    {
        "topic": "all_users",
        "title": "System Maintenance",
        "body": "The system will be under maintenance tonight",
        "data": {}  # optional
    }
    """
    # Check if user is staff/admin
    if not request.user.is_staff:
        return Response(
            {'error': 'Only admins can send topic notifications'},
            status=status.HTTP_403_FORBIDDEN
        )

    topic = request.data.get('topic')
    title = request.data.get('title')
    body = request.data.get('body')
    data = request.data.get('data', {})

    if not all([topic, title, body]):
        return Response(
            {'error': 'topic, title, and body are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        result = FCMService.send_to_topic(
            topic=topic,
            title=title,
            body=body,
            data=data
        )

        if result['success']:
            return Response({
                'message': 'Topic notification sent successfully',
                'message_id': result['message_id']
            })
        else:
            return Response(
                {'error': result.get('error', 'Failed to send notification')},
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def subscribe_to_topic(request):
    """
    Subscribe user's devices to a topic

    POST /api/services/fcm/topic/subscribe/
    {
        "topic": "providers"
    }
    """
    topic = request.data.get('topic')

    if not topic:
        return Response(
            {'error': 'topic is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        devices = FCMDevice.objects.filter(user=request.user, is_active=True)
        device_tokens = [device.device_token for device in devices]

        if not device_tokens:
            return Response(
                {'error': 'No active devices found'},
                status=status.HTTP_404_NOT_FOUND
            )

        result = FCMService.subscribe_to_topic(device_tokens, topic)

        if result['success']:
            return Response({
                'message': f'Subscribed to topic: {topic}',
                'success_count': result['success_count'],
                'failure_count': result['failure_count']
            })
        else:
            return Response(
                {'error': result.get('error', 'Failed to subscribe')},
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def unsubscribe_from_topic(request):
    """
    Unsubscribe user's devices from a topic

    POST /api/services/fcm/topic/unsubscribe/
    {
        "topic": "providers"
    }
    """
    topic = request.data.get('topic')

    if not topic:
        return Response(
            {'error': 'topic is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        devices = FCMDevice.objects.filter(user=request.user, is_active=True)
        device_tokens = [device.device_token for device in devices]

        if not device_tokens:
            return Response(
                {'error': 'No active devices found'},
                status=status.HTTP_404_NOT_FOUND
            )

        result = FCMService.unsubscribe_from_topic(device_tokens, topic)

        if result['success']:
            return Response({
                'message': f'Unsubscribed from topic: {topic}',
                'success_count': result['success_count'],
                'failure_count': result['failure_count']
            })
        else:
            return Response(
                {'error': result.get('error', 'Failed to unsubscribe')},
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_fcm_config(request):
    """
    Get FCM configuration for client initialization

    GET /api/services/fcm/config/
    """
    from django.conf import settings

    return Response({
        'sender_id': settings.FCM_SENDER_ID,
        'enabled': bool(settings.FCM_SERVER_KEY)
    })
