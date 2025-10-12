"""
Stripe Payment Service
Handles all Stripe payment operations including:
- Payment Intents
- Customers
- Payment Methods
- Refunds
- Webhooks
"""

import stripe
from django.conf import settings
from decimal import Decimal
from typing import Optional, Dict, Any

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = settings.STRIPE_API_VERSION


class StripeService:
    """Service class for handling Stripe operations"""

    @staticmethod
    def create_customer(email: str, name: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a Stripe customer

        Args:
            email: Customer email
            name: Customer name
            metadata: Additional metadata

        Returns:
            Dict containing customer information
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            return {
                'success': True,
                'customer_id': customer.id,
                'customer': customer
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def get_customer(customer_id: str) -> Dict[str, Any]:
        """Get Stripe customer by ID"""
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return {
                'success': True,
                'customer': customer
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def create_payment_intent(
        amount: Decimal,
        currency: str = None,
        customer_id: Optional[str] = None,
        payment_method_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        automatic_payment_methods: bool = True
    ) -> Dict[str, Any]:
        """
        Create a payment intent

        Args:
            amount: Amount in decimal (e.g., 10.50)
            currency: Currency code (default from settings)
            customer_id: Stripe customer ID
            payment_method_id: Stripe payment method ID
            metadata: Additional metadata
            automatic_payment_methods: Enable automatic payment methods

        Returns:
            Dict containing payment intent information
        """
        try:
            # Convert amount to cents (Stripe expects smallest currency unit)
            amount_cents = int(amount * 100)

            intent_params = {
                'amount': amount_cents,
                'currency': currency or settings.STRIPE_CURRENCY,
                'metadata': metadata or {}
            }

            if customer_id:
                intent_params['customer'] = customer_id

            if payment_method_id:
                intent_params['payment_method'] = payment_method_id
                intent_params['confirm'] = True
            elif automatic_payment_methods:
                intent_params['automatic_payment_methods'] = {'enabled': True}

            payment_intent = stripe.PaymentIntent.create(**intent_params)

            return {
                'success': True,
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'status': payment_intent.status,
                'payment_intent': payment_intent
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def confirm_payment_intent(payment_intent_id: str, payment_method_id: Optional[str] = None) -> Dict[str, Any]:
        """Confirm a payment intent"""
        try:
            params = {}
            if payment_method_id:
                params['payment_method'] = payment_method_id

            payment_intent = stripe.PaymentIntent.confirm(payment_intent_id, **params)

            return {
                'success': True,
                'status': payment_intent.status,
                'payment_intent': payment_intent
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def get_payment_intent(payment_intent_id: str) -> Dict[str, Any]:
        """Retrieve a payment intent"""
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                'success': True,
                'payment_intent': payment_intent,
                'status': payment_intent.status
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def cancel_payment_intent(payment_intent_id: str) -> Dict[str, Any]:
        """Cancel a payment intent"""
        try:
            payment_intent = stripe.PaymentIntent.cancel(payment_intent_id)
            return {
                'success': True,
                'payment_intent': payment_intent,
                'status': payment_intent.status
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def create_refund(
        payment_intent_id: Optional[str] = None,
        charge_id: Optional[str] = None,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a refund

        Args:
            payment_intent_id: Payment intent to refund
            charge_id: Charge to refund (alternative to payment_intent_id)
            amount: Amount to refund (None for full refund)
            reason: Reason for refund

        Returns:
            Dict containing refund information
        """
        try:
            refund_params = {}

            if payment_intent_id:
                refund_params['payment_intent'] = payment_intent_id
            elif charge_id:
                refund_params['charge'] = charge_id
            else:
                return {
                    'success': False,
                    'error': 'Either payment_intent_id or charge_id must be provided'
                }

            if amount:
                refund_params['amount'] = int(amount * 100)

            if reason:
                refund_params['reason'] = reason

            refund = stripe.Refund.create(**refund_params)

            return {
                'success': True,
                'refund_id': refund.id,
                'status': refund.status,
                'amount': Decimal(refund.amount) / 100,
                'refund': refund
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def attach_payment_method(payment_method_id: str, customer_id: str) -> Dict[str, Any]:
        """Attach a payment method to a customer"""
        try:
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )
            return {
                'success': True,
                'payment_method': payment_method
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def detach_payment_method(payment_method_id: str) -> Dict[str, Any]:
        """Detach a payment method from a customer"""
        try:
            payment_method = stripe.PaymentMethod.detach(payment_method_id)
            return {
                'success': True,
                'payment_method': payment_method
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def list_payment_methods(customer_id: str, method_type: str = 'card') -> Dict[str, Any]:
        """List payment methods for a customer"""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type=method_type
            )
            return {
                'success': True,
                'payment_methods': payment_methods.data
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def create_setup_intent(customer_id: str) -> Dict[str, Any]:
        """
        Create a setup intent for saving payment methods
        Used for future payments without immediate charge
        """
        try:
            setup_intent = stripe.SetupIntent.create(
                customer=customer_id,
                payment_method_types=['card']
            )
            return {
                'success': True,
                'setup_intent_id': setup_intent.id,
                'client_secret': setup_intent.client_secret,
                'setup_intent': setup_intent
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def construct_webhook_event(payload: bytes, sig_header: str) -> Dict[str, Any]:
        """
        Construct and verify a webhook event

        Args:
            payload: Request body
            sig_header: Stripe signature header

        Returns:
            Dict containing event information
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                settings.STRIPE_WEBHOOK_SECRET
            )
            return {
                'success': True,
                'event': event
            }
        except ValueError:
            return {
                'success': False,
                'error': 'Invalid payload'
            }
        except stripe.error.SignatureVerificationError:
            return {
                'success': False,
                'error': 'Invalid signature'
            }

    @staticmethod
    def get_balance() -> Dict[str, Any]:
        """Get Stripe account balance"""
        try:
            balance = stripe.Balance.retrieve()
            return {
                'success': True,
                'balance': balance
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def create_transfer(
        amount: Decimal,
        destination: str,
        currency: str = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a transfer to a connected account (for provider payouts)

        Args:
            amount: Amount to transfer
            destination: Connected account ID
            currency: Currency code
            metadata: Additional metadata

        Returns:
            Dict containing transfer information
        """
        try:
            transfer = stripe.Transfer.create(
                amount=int(amount * 100),
                currency=currency or settings.STRIPE_CURRENCY,
                destination=destination,
                metadata=metadata or {}
            )
            return {
                'success': True,
                'transfer_id': transfer.id,
                'transfer': transfer
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }
