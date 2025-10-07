from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from math import radians, cos, sin, asin, sqrt
from .models import (
    ServiceCategory, ProviderProfile, Service, Booking, Review,
    Payment, Installment, UserCredits, Address, Conversation, Message,
    Notification, NotificationPreference
)
from .serializers import (
    ServiceCategorySerializer, ProviderProfileSerializer,
    ServiceListSerializer, ServiceDetailSerializer, ServiceCreateUpdateSerializer,
    BookingSerializer, ReviewSerializer, ProviderDashboardSerializer,
    PaymentSerializer, PaymentProcessSerializer, UserCreditsSerializer,
    UserCreditsBalanceSerializer, AddressSerializer, ConversationSerializer,
    MessageSerializer, NotificationSerializer, NotificationPreferenceSerializer
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


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_booking_review_view(request, booking_id):
    """Create a review for a completed booking"""
    try:
        booking = Booking.objects.get(id=booking_id, customer=request.user)

        # Check if booking is completed
        if booking.status != 'completed':
            return Response({'error': 'Can only review completed bookings'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Check if review already exists
        if hasattr(booking, 'review'):
            return Response({'error': 'Booking already reviewed'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Create review
        rating = request.data.get('rating')
        comment = request.data.get('comment', '')

        if not rating or not (1 <= int(rating) <= 5):
            return Response({'error': 'Rating must be between 1 and 5'},
                          status=status.HTTP_400_BAD_REQUEST)

        review = Review.objects.create(
            booking=booking,
            service=booking.service,
            customer=booking.customer,
            provider=booking.provider,
            rating=rating,
            comment=comment
        )

        # Update provider rating
        provider_profile = booking.provider.provider_profile
        provider_profile.update_rating()

        # Update service average rating (implicit through property)

        # Create notification for provider
        Notification.objects.create(
            user=booking.provider,
            notification_type='review',
            title='New Review',
            message=f'{booking.customer.name} left a {rating}-star review',
            booking=booking
        )

        serializer = ReviewSerializer(review)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'},
                       status=status.HTTP_404_NOT_FOUND)


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


# Provider Earnings & Analytics
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def provider_earnings_view(request):
    """Get detailed provider earnings breakdown"""
    try:
        profile = request.user.provider_profile

        # Filter by date range if provided
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        bookings = Booking.objects.filter(
            provider=request.user,
            status='completed',
            is_paid=True
        )

        if start_date:
            bookings = bookings.filter(created_at__gte=start_date)
        if end_date:
            bookings = bookings.filter(created_at__lte=end_date)

        total_earnings = bookings.aggregate(total=Sum('total_amount'))['total'] or 0

        # Group by month
        from django.db.models.functions import TruncMonth
        monthly_earnings = bookings.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            amount=Sum('total_amount'),
            count=Count('id')
        ).order_by('-month')[:12]

        return Response({
            'total_earnings': profile.total_earnings,
            'period_earnings': total_earnings,
            'monthly_breakdown': list(monthly_earnings),
            'completed_jobs': bookings.count(),
            'average_per_job': total_earnings / bookings.count() if bookings.count() > 0 else 0
        })

    except ProviderProfile.DoesNotExist:
        return Response({'error': 'Provider profile not found'},
                       status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def provider_analytics_view(request):
    """Get provider performance analytics"""
    try:
        profile = request.user.provider_profile

        # Booking statistics
        total_bookings = Booking.objects.filter(provider=request.user).count()
        completed_bookings = Booking.objects.filter(provider=request.user, status='completed').count()
        cancelled_bookings = Booking.objects.filter(provider=request.user, status='cancelled').count()

        # Rating analysis
        reviews = Review.objects.filter(provider=request.user)
        rating_breakdown = reviews.values('rating').annotate(count=Count('id'))

        # Service performance
        top_services = Service.objects.filter(provider=request.user).annotate(
            booking_count=Count('bookings')
        ).order_by('-booking_count')[:5]

        return Response({
            'overview': {
                'rating': float(profile.rating),
                'total_earnings': float(profile.total_earnings),
                'jobs_completed': profile.jobs_completed,
                'total_bookings': total_bookings,
                'completion_rate': (completed_bookings / total_bookings * 100) if total_bookings > 0 else 0,
                'cancellation_rate': (cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0
            },
            'rating_breakdown': list(rating_breakdown),
            'top_services': ServiceListSerializer(top_services, many=True).data,
            'total_reviews': reviews.count()
        })

    except ProviderProfile.DoesNotExist:
        return Response({'error': 'Provider profile not found'},
                       status=status.HTTP_404_NOT_FOUND)


# Provider Schedule Management
@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated])
def provider_schedule_view(request):
    """Get or update provider's availability schedule"""
    try:
        profile = request.user.provider_profile

        if request.method == 'GET':
            # Return schedule (for now, just availability status)
            return Response({
                'is_available': profile.is_available,
                'schedule': {}  # TODO: Implement detailed schedule with time slots
            })

        elif request.method == 'PUT':
            is_available = request.data.get('is_available')
            if is_available is not None:
                profile.is_available = is_available
                profile.save()

            return Response({
                'is_available': profile.is_available,
                'message': 'Schedule updated successfully'
            })

    except ProviderProfile.DoesNotExist:
        return Response({'error': 'Provider profile not found'},
                       status=status.HTTP_404_NOT_FOUND)


# Location-based Services
def haversine_distance(lon1, lat1, lon2, lat2):
    """Calculate distance between two points in km"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def nearby_services_view(request):
    """Get services near a location"""
    latitude = request.query_params.get('latitude')
    longitude = request.query_params.get('longitude')
    radius = float(request.query_params.get('radius', 10))  # Default 10km

    if not latitude or not longitude:
        return Response({'error': 'Latitude and longitude are required'},
                       status=status.HTTP_400_BAD_REQUEST)

    try:
        lat = float(latitude)
        lon = float(longitude)

        # Get all active services
        services = Service.objects.filter(is_active=True).select_related('provider', 'category')

        # Filter by distance (simplified - in production use PostGIS)
        nearby_services = []
        for service in services:
            # Get provider's default address
            provider_address = Address.objects.filter(
                user=service.provider,
                is_default=True
            ).first()

            if provider_address and provider_address.latitude and provider_address.longitude:
                distance = haversine_distance(
                    lon, lat,
                    float(provider_address.longitude),
                    float(provider_address.latitude)
                )

                if distance <= radius:
                    nearby_services.append({
                        'service': ServiceListSerializer(service).data,
                        'distance_km': round(distance, 2)
                    })

        # Sort by distance
        nearby_services.sort(key=lambda x: x['distance_km'])

        return Response({
            'count': len(nearby_services),
            'results': nearby_services
        })

    except ValueError:
        return Response({'error': 'Invalid coordinates'},
                       status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def geocode_location_view(request):
    """Convert address to coordinates (placeholder - integrate with Google Maps API)"""
    address = request.data.get('address')

    if not address:
        return Response({'error': 'Address is required'},
                       status=status.HTTP_400_BAD_REQUEST)

    # TODO: Integrate with geocoding service (Google Maps, Mapbox, etc.)
    return Response({
        'address': address,
        'latitude': None,
        'longitude': None,
        'message': 'Geocoding service not yet integrated'
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def validate_address_view(request):
    """Validate address format"""
    street_address = request.data.get('street_address')
    city = request.data.get('city')
    postal_code = request.data.get('postal_code')
    country = request.data.get('country')

    errors = []
    if not street_address:
        errors.append('Street address is required')
    if not city:
        errors.append('City is required')
    if not postal_code:
        errors.append('Postal code is required')
    if not country:
        errors.append('Country is required')

    if errors:
        return Response({'valid': False, 'errors': errors},
                       status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'valid': True,
        'message': 'Address is valid'
    })


# Review Management
@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def respond_to_review_view(request, review_id):
    """Provider responds to a review"""
    try:
        review = Review.objects.get(id=review_id, provider=request.user)
        provider_response = request.data.get('provider_response')

        if not provider_response:
            return Response({'error': 'Response text is required'},
                          status=status.HTTP_400_BAD_REQUEST)

        review.provider_response = provider_response
        review.save()

        serializer = ReviewSerializer(review)
        return Response(serializer.data)

    except Review.DoesNotExist:
        return Response({'error': 'Review not found'},
                       status=status.HTTP_404_NOT_FOUND)


# Payment Management
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_methods_view(request):
    """Get user's saved payment methods (placeholder)"""
    # TODO: Integrate with Stripe/PayPal to get saved payment methods
    return Response({
        'payment_methods': [],
        'message': 'Payment gateway integration pending'
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def refund_payment_view(request):
    """Process payment refund"""
    payment_id = request.data.get('payment_id')
    reason = request.data.get('reason', '')

    try:
        payment = Payment.objects.get(id=payment_id, user=request.user)

        if payment.status == 'refunded':
            return Response({'error': 'Payment already refunded'},
                          status=status.HTTP_400_BAD_REQUEST)

        if payment.status != 'completed':
            return Response({'error': 'Only completed payments can be refunded'},
                          status=status.HTTP_400_BAD_REQUEST)

        # TODO: Process refund through payment gateway

        payment.status = 'refunded'
        payment.save()

        # Update booking status
        payment.booking.status = 'cancelled'
        payment.booking.save()

        serializer = PaymentSerializer(payment)
        return Response({
            'payment': serializer.data,
            'message': 'Refund processed successfully'
        })

    except Payment.DoesNotExist:
        return Response({'error': 'Payment not found'},
                       status=status.HTTP_404_NOT_FOUND)


# Chat & Messaging Views
class ConversationListCreateView(generics.ListCreateAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            Q(customer=user) | Q(provider=user)
        ).distinct()

    def perform_create(self, serializer):
        # Determine customer and provider based on current user
        booking_id = self.request.data.get('booking')
        if booking_id:
            booking = Booking.objects.get(id=booking_id)
            serializer.save(
                customer=booking.customer,
                provider=booking.provider,
                booking=booking
            )


class ConversationDetailView(generics.RetrieveAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            Q(customer=user) | Q(provider=user)
        )


class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.request.query_params.get('conversation_id')
        if conversation_id:
            return Message.objects.filter(
                conversation_id=conversation_id,
                conversation__in=Conversation.objects.filter(
                    Q(customer=self.request.user) | Q(provider=self.request.user)
                )
            )
        return Message.objects.none()

    def perform_create(self, serializer):
        message = serializer.save(sender=self.request.user)

        # Update conversation last_message_at
        conversation = message.conversation
        conversation.last_message_at = timezone.now()
        conversation.save()

        # Create notification for the recipient
        recipient = conversation.provider if message.sender == conversation.customer else conversation.customer
        Notification.objects.create(
            user=recipient,
            notification_type='message',
            title='New Message',
            message=f'You have a new message from {message.sender.name}',
            booking=conversation.booking
        )


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def mark_messages_read_view(request, conversation_id):
    """Mark all messages in a conversation as read"""
    try:
        conversation = Conversation.objects.filter(
            Q(customer=request.user) | Q(provider=request.user),
            id=conversation_id
        ).first()

        if not conversation:
            return Response({'error': 'Conversation not found'},
                          status=status.HTTP_404_NOT_FOUND)

        # Mark all messages from other user as read
        Message.objects.filter(
            conversation=conversation
        ).exclude(sender=request.user).update(is_read=True)

        return Response({'message': 'Messages marked as read'})

    except Exception as e:
        return Response({'error': str(e)},
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Notification Views
class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        notification_type = self.request.query_params.get('type')
        unread_only = self.request.query_params.get('unread_only', 'false').lower() == 'true'

        queryset = Notification.objects.filter(user=user)

        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        if unread_only:
            queryset = queryset.filter(is_read=False)

        return queryset


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_read_view(request, notification_id):
    """Mark a notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'},
                       status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_notifications_read_view(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({'message': 'All notifications marked as read'})


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_notification_view(request, notification_id):
    """Delete a notification"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.delete()
        return Response({'message': 'Notification deleted'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'},
                       status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_count_view(request):
    """Get count of unread notifications"""
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return Response({'unread_count': unread_count})


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        preference, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preference


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_notification_view(request):
    """Send a notification to a user (admin/system use)"""
    user_id = request.data.get('user_id')
    notification_type = request.data.get('notification_type')
    title = request.data.get('title')
    message = request.data.get('message')

    if not all([user_id, notification_type, title, message]):
        return Response({'error': 'Missing required fields'},
                       status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(id=user_id)
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message
        )
        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except User.DoesNotExist:
        return Response({'error': 'User not found'},
                       status=status.HTTP_404_NOT_FOUND)
