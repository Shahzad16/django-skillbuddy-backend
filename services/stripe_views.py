"""
Stripe Payment Views
All Stripe-related API endpoints
"""

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
from django.db import transaction
from .stripe_service import StripeService
from .models import Payment, Booking, User, Installment
from .serializers import PaymentSerializer
from decimal import Decimal
import json


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_stripe_publishable_key(request):
    """Get Stripe publishable key for client-side initialization"""
    return Response({
        'publishable_key': settings.STRIPE_PUBLISHABLE_KEY
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_payment_intent(request):
    """
    Create a Stripe payment intent for a booking

    Request body:
    {
        "booking_id": 123,
        "save_payment_method": false  # optional
    }
    """
    booking_id = request.data.get('booking_id')
    save_payment_method = request.data.get('save_payment_method', False)

    if not booking_id:
        return Response(
            {'error': 'booking_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        booking = Booking.objects.get(id=booking_id, customer=request.user)

        if booking.is_paid:
            return Response(
                {'error': 'Booking is already paid'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create Stripe customer
        user = request.user
        if not hasattr(user, 'stripe_customer_id') or not user.stripe_customer_id:
            customer_result = StripeService.create_customer(
                email=user.email,
                name=user.name or user.username,
                metadata={'user_id': user.id}
            )

            if not customer_result['success']:
                return Response(
                    {'error': customer_result['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Save customer ID (you'll need to add this field to User model)
            # user.stripe_customer_id = customer_result['customer_id']
            # user.save()
            customer_id = customer_result['customer_id']
        else:
            customer_id = user.stripe_customer_id

        # Create payment intent
        intent_result = StripeService.create_payment_intent(
            amount=booking.total_amount,
            customer_id=customer_id,
            metadata={
                'booking_id': booking.id,
                'user_id': user.id,
                'service_id': booking.service.id
            }
        )

        if not intent_result['success']:
            return Response(
                {'error': intent_result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create payment record
        payment = Payment.objects.create(
            booking=booking,
            user=user,
            amount=booking.total_amount,
            payment_type='immediate',
            payment_method='card',
            status='processing',
            transaction_id=intent_result['payment_intent_id']
        )

        return Response({
            'payment_intent_id': intent_result['payment_intent_id'],
            'client_secret': intent_result['client_secret'],
            'payment_id': payment.id,
            'amount': float(booking.total_amount)
        }, status=status.HTTP_201_CREATED)

    except Booking.DoesNotExist:
        return Response(
            {'error': 'Booking not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirm_payment(request):
    """
    Confirm payment after client-side confirmation

    Request body:
    {
        "payment_intent_id": "pi_xxx"
    }
    """
    payment_intent_id = request.data.get('payment_intent_id')

    if not payment_intent_id:
        return Response(
            {'error': 'payment_intent_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Get payment intent from Stripe
        intent_result = StripeService.get_payment_intent(payment_intent_id)

        if not intent_result['success']:
            return Response(
                {'error': intent_result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_intent = intent_result['payment_intent']

        # Update payment record
        payment = Payment.objects.get(transaction_id=payment_intent_id)

        if payment_intent.status == 'succeeded':
            payment.status = 'completed'
            payment.booking.is_paid = True
            payment.booking.save()
        elif payment_intent.status in ['processing', 'requires_action']:
            payment.status = 'processing'
        else:
            payment.status = 'failed'

        payment.gateway_response = payment_intent
        payment.save()

        return Response({
            'payment_id': payment.id,
            'status': payment.status,
            'payment_intent_status': payment_intent.status
        })

    except Payment.DoesNotExist:
        return Response(
            {'error': 'Payment not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_payment_status(request, payment_intent_id):
    """Get the status of a payment intent"""
    try:
        intent_result = StripeService.get_payment_intent(payment_intent_id)

        if not intent_result['success']:
            return Response(
                {'error': intent_result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_intent = intent_result['payment_intent']

        return Response({
            'payment_intent_id': payment_intent.id,
            'status': payment_intent.status,
            'amount': Decimal(payment_intent.amount) / 100,
            'currency': payment_intent.currency
        })

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_refund(request):
    """
    Create a refund for a payment

    Request body:
    {
        "payment_id": 123,
        "amount": 50.00,  # optional, for partial refund
        "reason": "requested_by_customer"  # optional
    }
    """
    payment_id = request.data.get('payment_id')
    amount = request.data.get('amount')
    reason = request.data.get('reason')

    if not payment_id:
        return Response(
            {'error': 'payment_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        payment = Payment.objects.get(id=payment_id, user=request.user)

        if payment.status != 'completed':
            return Response(
                {'error': 'Can only refund completed payments'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if payment.status == 'refunded':
            return Response(
                {'error': 'Payment already refunded'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create refund in Stripe
        refund_amount = Decimal(amount) if amount else None
        refund_result = StripeService.create_refund(
            payment_intent_id=payment.transaction_id,
            amount=refund_amount,
            reason=reason
        )

        if not refund_result['success']:
            return Response(
                {'error': refund_result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update payment status
        payment.status = 'refunded'
        payment.save()

        # Update booking
        payment.booking.status = 'cancelled'
        payment.booking.save()

        return Response({
            'refund_id': refund_result['refund_id'],
            'amount': float(refund_result['amount']),
            'status': refund_result['status'],
            'message': 'Refund processed successfully'
        })

    except Payment.DoesNotExist:
        return Response(
            {'error': 'Payment not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_setup_intent(request):
    """
    Create a setup intent for saving payment methods
    Used to save cards for future use without charging
    """
    user = request.user

    try:
        # Get or create Stripe customer
        if not hasattr(user, 'stripe_customer_id') or not user.stripe_customer_id:
            customer_result = StripeService.create_customer(
                email=user.email,
                name=user.name or user.username,
                metadata={'user_id': user.id}
            )

            if not customer_result['success']:
                return Response(
                    {'error': customer_result['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            customer_id = customer_result['customer_id']
        else:
            customer_id = user.stripe_customer_id

        # Create setup intent
        setup_result = StripeService.create_setup_intent(customer_id)

        if not setup_result['success']:
            return Response(
                {'error': setup_result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'setup_intent_id': setup_result['setup_intent_id'],
            'client_secret': setup_result['client_secret']
        })

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_payment_methods(request):
    """List saved payment methods for the user"""
    user = request.user

    if not hasattr(user, 'stripe_customer_id') or not user.stripe_customer_id:
        return Response({'payment_methods': []})

    try:
        methods_result = StripeService.list_payment_methods(user.stripe_customer_id)

        if not methods_result['success']:
            return Response(
                {'error': methods_result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_methods = []
        for pm in methods_result['payment_methods']:
            payment_methods.append({
                'id': pm.id,
                'type': pm.type,
                'card': {
                    'brand': pm.card.brand,
                    'last4': pm.card.last4,
                    'exp_month': pm.card.exp_month,
                    'exp_year': pm.card.exp_year
                } if pm.type == 'card' else None
            })

        return Response({'payment_methods': payment_methods})

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def attach_payment_method(request):
    """
    Attach a payment method to the user's customer

    Request body:
    {
        "payment_method_id": "pm_xxx"
    }
    """
    payment_method_id = request.data.get('payment_method_id')
    user = request.user

    if not payment_method_id:
        return Response(
            {'error': 'payment_method_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        if not hasattr(user, 'stripe_customer_id') or not user.stripe_customer_id:
            return Response(
                {'error': 'User does not have a Stripe customer'},
                status=status.HTTP_400_BAD_REQUEST
            )

        attach_result = StripeService.attach_payment_method(
            payment_method_id,
            user.stripe_customer_id
        )

        if not attach_result['success']:
            return Response(
                {'error': attach_result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'message': 'Payment method attached successfully',
            'payment_method_id': payment_method_id
        })

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def detach_payment_method(request):
    """
    Detach (remove) a payment method

    Request body:
    {
        "payment_method_id": "pm_xxx"
    }
    """
    payment_method_id = request.data.get('payment_method_id')

    if not payment_method_id:
        return Response(
            {'error': 'payment_method_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        detach_result = StripeService.detach_payment_method(payment_method_id)

        if not detach_result['success']:
            return Response(
                {'error': detach_result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'message': 'Payment method removed successfully'
        })

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def stripe_webhook(request):
    """
    Handle Stripe webhook events

    Important: This endpoint should be configured in your Stripe Dashboard
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    if not sig_header:
        return HttpResponse(status=400)

    # Verify webhook signature
    event_result = StripeService.construct_webhook_event(payload, sig_header)

    if not event_result['success']:
        return HttpResponse(status=400)

    event = event_result['event']
    event_type = event['type']

    try:
        # Handle different event types
        if event_type == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            _handle_payment_intent_succeeded(payment_intent)

        elif event_type == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            _handle_payment_intent_failed(payment_intent)

        elif event_type == 'payment_intent.canceled':
            payment_intent = event['data']['object']
            _handle_payment_intent_canceled(payment_intent)

        elif event_type == 'charge.refunded':
            charge = event['data']['object']
            _handle_charge_refunded(charge)

        elif event_type == 'customer.created':
            customer = event['data']['object']
            _handle_customer_created(customer)

        elif event_type == 'payment_method.attached':
            payment_method = event['data']['object']
            _handle_payment_method_attached(payment_method)

        # Add more event handlers as needed

        return HttpResponse(status=200)

    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return HttpResponse(status=500)


def _handle_payment_intent_succeeded(payment_intent):
    """Handle successful payment intent"""
    try:
        payment = Payment.objects.get(transaction_id=payment_intent['id'])
        payment.status = 'completed'
        payment.gateway_response = payment_intent
        payment.save()

        # Mark booking as paid
        booking = payment.booking
        booking.is_paid = True
        booking.status = 'confirmed'
        booking.save()

        # TODO: Send confirmation email/notification

    except Payment.DoesNotExist:
        pass


def _handle_payment_intent_failed(payment_intent):
    """Handle failed payment intent"""
    try:
        payment = Payment.objects.get(transaction_id=payment_intent['id'])
        payment.status = 'failed'
        payment.gateway_response = payment_intent
        payment.save()

        # TODO: Send failure notification

    except Payment.DoesNotExist:
        pass


def _handle_payment_intent_canceled(payment_intent):
    """Handle canceled payment intent"""
    try:
        payment = Payment.objects.get(transaction_id=payment_intent['id'])
        payment.status = 'failed'
        payment.gateway_response = payment_intent
        payment.save()

    except Payment.DoesNotExist:
        pass


def _handle_charge_refunded(charge):
    """Handle refunded charge"""
    # Find payment by charge ID and update status
    try:
        payment = Payment.objects.filter(
            transaction_id=charge.get('payment_intent')
        ).first()

        if payment:
            payment.status = 'refunded'
            payment.save()

    except Exception:
        pass


def _handle_customer_created(customer):
    """Handle customer creation"""
    # You can use this to sync customer data
    pass


def _handle_payment_method_attached(payment_method):
    """Handle payment method attachment"""
    # You can use this to track payment methods
    pass
