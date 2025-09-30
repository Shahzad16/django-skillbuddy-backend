from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import timedelta
from .models import (
    ServiceCategory, ProviderProfile, Service, Booking, Review,
    Payment, Installment, UserCredits, Address
)
from .serializers import (
    ServiceCategorySerializer, ProviderProfileSerializer,
    ServiceListSerializer, ServiceDetailSerializer, ServiceCreateUpdateSerializer,
    BookingSerializer, ReviewSerializer, ProviderDashboardSerializer,
    PaymentSerializer, PaymentProcessSerializer, UserCreditsSerializer,
    UserCreditsBalanceSerializer, AddressSerializer
)


class ServiceCategoryListView(generics.ListCreateAPIView):
    queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ServiceCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ServiceListView(generics.ListAPIView):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'provider']
    search_fields = ['title', 'description', 'provider__name']
    ordering_fields = ['created_at', 'price', 'average_rating']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get('category_id')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')

        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        return queryset


class ServiceDetailView(generics.RetrieveAPIView):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceDetailSerializer
    permission_classes = [permissions.AllowAny]


class ServiceCreateView(generics.CreateAPIView):
    serializer_class = ServiceCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Ensure user has a provider profile
        provider_profile, created = ProviderProfile.objects.get_or_create(
            user=self.request.user
        )
        serializer.save()


class ServiceUpdateView(generics.UpdateAPIView):
    serializer_class = ServiceCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Service.objects.filter(provider=self.request.user)


class ServiceDeleteView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Service.objects.filter(provider=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def popular_services_view(request):
    """Get popular services based on booking count and ratings"""
    services = Service.objects.filter(is_active=True).order_by('-bookings__count')[:10]
    serializer = ServiceListSerializer(services, many=True)
    return Response(serializer.data)


class ProviderProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProviderProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, created = ProviderProfile.objects.get_or_create(
            user=self.request.user
        )
        return profile


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def become_provider_view(request):
    """Register user as a service provider"""
    try:
        profile = ProviderProfile.objects.get(user=request.user)
        return Response({'message': 'User is already a provider'},
                       status=status.HTTP_400_BAD_REQUEST)
    except ProviderProfile.DoesNotExist:
        serializer = ProviderProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BookingListCreateView(generics.ListCreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = self.request.query_params.get('role', 'customer')

        if role == 'provider':
            return Booking.objects.filter(provider=user)
        return Booking.objects.filter(customer=user)


class BookingDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Booking.objects.filter(
            Q(customer=user) | Q(provider=user)
        )


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_booking_status_view(request, booking_id):
    """Update booking status (for providers)"""
    try:
        booking = Booking.objects.get(id=booking_id, provider=request.user)
        new_status = request.data.get('status')

        if new_status not in dict(Booking.BOOKING_STATUS):
            return Response({'error': 'Invalid status'},
                          status=status.HTTP_400_BAD_REQUEST)

        booking.status = new_status
        booking.save()

        # Update provider profile stats if completed
        if new_status == 'completed':
            profile = booking.provider.provider_profile
            profile.jobs_completed += 1
            profile.total_earnings += booking.total_amount
            profile.save()

        serializer = BookingSerializer(booking)
        return Response(serializer.data)

    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'},
                       status=status.HTTP_404_NOT_FOUND)


class ReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        service_id = self.request.query_params.get('service_id')
        provider_id = self.request.query_params.get('provider_id')

        queryset = Review.objects.all()
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        if provider_id:
            queryset = queryset.filter(provider_id=provider_id)

        return queryset


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def provider_dashboard_view(request):
    """Get provider dashboard data"""
    try:
        profile = request.user.provider_profile
        serializer = ProviderDashboardSerializer(profile)
        return Response(serializer.data)
    except ProviderProfile.DoesNotExist:
        return Response({'error': 'Provider profile not found'},
                       status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def reschedule_booking_view(request, booking_id):
    """Reschedule a booking"""
    try:
        booking = Booking.objects.get(id=booking_id, customer=request.user)

        if booking.status not in ['pending', 'confirmed']:
            return Response({'error': 'Cannot reschedule booking in current status'},
                          status=status.HTTP_400_BAD_REQUEST)

        scheduled_date = request.data.get('scheduled_date')
        scheduled_time = request.data.get('scheduled_time')

        if scheduled_date:
            booking.scheduled_date = scheduled_date
        if scheduled_time:
            booking.scheduled_time = scheduled_time

        booking.save()
        serializer = BookingSerializer(booking)
        return Response(serializer.data)

    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'},
                       status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def cancel_booking_view(request, booking_id):
    """Cancel a booking"""
    try:
        booking = Booking.objects.filter(
            Q(customer=request.user) | Q(provider=request.user),
            id=booking_id
        ).first()

        if not booking:
            return Response({'error': 'Booking not found'},
                          status=status.HTTP_404_NOT_FOUND)

        if booking.status in ['completed', 'cancelled']:
            return Response({'error': 'Cannot cancel booking in current status'},
                          status=status.HTTP_400_BAD_REQUEST)

        booking.status = 'cancelled'
        booking.save()

        # Refund credits if used
        if booking.payment_method == 'credits' and booking.is_paid:
            user_balance = UserCredits.objects.filter(user=booking.customer).aggregate(
                total=Sum('amount')
            )['total'] or 0

            UserCredits.objects.create(
                user=booking.customer,
                amount=booking.service.credits_required,
                transaction_type='refund',
                description=f'Refund for cancelled booking #{booking.id}',
                booking=booking,
                balance_after=user_balance + booking.service.credits_required
            )

        serializer = BookingSerializer(booking)
        return Response(serializer.data)

    except Exception as e:
        return Response({'error': str(e)},
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def accept_job_view(request, booking_id):
    """Provider accepts a job request"""
    try:
        booking = Booking.objects.get(id=booking_id, provider=request.user)

        if booking.status != 'pending':
            return Response({'error': 'Job request is not pending'},
                          status=status.HTTP_400_BAD_REQUEST)

        booking.status = 'confirmed'
        booking.save()

        serializer = BookingSerializer(booking)
        return Response(serializer.data)

    except Booking.DoesNotExist:
        return Response({'error': 'Job request not found'},
                       status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def decline_job_view(request, booking_id):
    """Provider declines a job request"""
    try:
        booking = Booking.objects.get(id=booking_id, provider=request.user)

        if booking.status != 'pending':
            return Response({'error': 'Job request is not pending'},
                          status=status.HTTP_400_BAD_REQUEST)

        booking.status = 'cancelled'
        booking.save()

        serializer = BookingSerializer(booking)
        return Response(serializer.data)

    except Booking.DoesNotExist:
        return Response({'error': 'Job request not found'},
                       status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def provider_jobs_view(request):
    """Get all job requests for provider"""
    status_filter = request.query_params.get('status', None)
    queryset = Booking.objects.filter(provider=request.user)

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    serializer = BookingSerializer(queryset, many=True)
    return Response(serializer.data)


# Payment Views
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def process_payment_view(request):
    """Process payment for a booking"""
    serializer = PaymentProcessSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    try:
        booking = Booking.objects.get(id=data['booking_id'], customer=request.user)

        if booking.is_paid:
            return Response({'error': 'Booking is already paid'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Handle credits payment
        if data['payment_method'] == 'credits':
            user_balance = UserCredits.objects.filter(user=request.user).aggregate(
                total=Sum('amount')
            )['total'] or 0

            if user_balance < booking.service.credits_required:
                return Response({'error': 'Insufficient credits'},
                              status=status.HTTP_400_BAD_REQUEST)

            # Deduct credits
            UserCredits.objects.create(
                user=request.user,
                amount=-booking.service.credits_required,
                transaction_type='used',
                description=f'Payment for booking #{booking.id}',
                booking=booking,
                balance_after=user_balance - booking.service.credits_required
            )

            payment = Payment.objects.create(
                booking=booking,
                user=request.user,
                amount=booking.total_amount,
                payment_type=data['payment_type'],
                payment_method=data['payment_method'],
                status='completed'
            )

            booking.is_paid = True
            booking.save()

        # Handle installment payment
        elif data['payment_type'] == 'installment':
            installment_count = data.get('installment_count', 3)
            installment_amount = booking.total_amount / installment_count

            payment = Payment.objects.create(
                booking=booking,
                user=request.user,
                amount=booking.total_amount,
                payment_type=data['payment_type'],
                payment_method=data['payment_method'],
                status='processing'
            )

            # Create installment records
            for i in range(installment_count):
                due_date = timezone.now().date() + timedelta(days=30 * (i + 1))
                Installment.objects.create(
                    payment=payment,
                    installment_number=i + 1,
                    amount=installment_amount,
                    due_date=due_date,
                    status='pending'
                )

        # Handle immediate and later payments (integrate with Stripe/PayPal here)
        else:
            payment = Payment.objects.create(
                booking=booking,
                user=request.user,
                amount=booking.total_amount,
                payment_type=data['payment_type'],
                payment_method=data['payment_method'],
                status='completed' if data['payment_type'] == 'immediate' else 'pending',
                transaction_id=f"TXN{booking.id}{timezone.now().timestamp()}"
            )

            if data['payment_type'] == 'immediate':
                booking.is_paid = True
                booking.save()

        response_serializer = PaymentSerializer(payment)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'},
                       status=status.HTTP_404_NOT_FOUND)


class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_credits_balance_view(request):
    """Get user's credit balance and recent transactions"""
    user_balance = UserCredits.objects.filter(user=request.user).aggregate(
        total=Sum('amount')
    )['total'] or 0

    recent_transactions = UserCredits.objects.filter(user=request.user)[:10]

    serializer = UserCreditsBalanceSerializer({
        'total_credits': user_balance,
        'recent_transactions': recent_transactions
    })

    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def purchase_credits_view(request):
    """Purchase credits"""
    amount = request.data.get('amount')

    if not amount or amount <= 0:
        return Response({'error': 'Invalid amount'},
                       status=status.HTTP_400_BAD_REQUEST)

    user_balance = UserCredits.objects.filter(user=request.user).aggregate(
        total=Sum('amount')
    )['total'] or 0

    UserCredits.objects.create(
        user=request.user,
        amount=amount,
        transaction_type='purchase',
        description=f'Purchased {amount} credits',
        balance_after=user_balance + amount
    )

    return Response({'message': 'Credits purchased successfully', 'balance': user_balance + amount})


class AddressListCreateView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
