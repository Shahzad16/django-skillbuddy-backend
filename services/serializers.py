from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    ServiceCategory, ProviderProfile, Service, ServiceImage,
    Booking, Review, Payment, Installment, UserCredits, Address,
    Conversation, Message, Notification, NotificationPreference, FCMDevice
)

User = get_user_model()


class ServiceCategorySerializer(serializers.ModelSerializer):
    services_count = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'description', 'icon', 'color', 'is_active',
                 'services_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_services_count(self, obj):
        return obj.services.filter(is_active=True).count()


class ServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImage
        fields = ['id', 'image_url', 'alt_text', 'is_primary', 'created_at']
        read_only_fields = ['created_at']


class ProviderProfileSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    skills_names = serializers.StringRelatedField(source='skills', many=True, read_only=True)

    class Meta:
        model = ProviderProfile
        fields = ['id', 'user', 'user_name', 'user_email', 'account_type',
                 'business_name', 'description', 'skills', 'skills_names',
                 'rating', 'total_earnings', 'jobs_completed', 'is_verified',
                 'is_available', 'created_at', 'updated_at']
        read_only_fields = ['user', 'rating', 'total_earnings', 'jobs_completed',
                           'created_at', 'updated_at']


class ServiceListSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    average_rating = serializers.ReadOnlyField()
    total_reviews = serializers.ReadOnlyField()

    class Meta:
        model = Service
        fields = ['id', 'title', 'description', 'price', 'credits_required',
                 'duration_minutes', 'provider_name', 'category_name',
                 'primary_image', 'average_rating', 'total_reviews',
                 'is_active', 'created_at']

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return primary_image.image_url
        return None


class ServiceDetailSerializer(serializers.ModelSerializer):
    provider = ProviderProfileSerializer(source='provider.provider_profile', read_only=True)
    category = ServiceCategorySerializer(read_only=True)
    images = ServiceImageSerializer(many=True, read_only=True)
    average_rating = serializers.ReadOnlyField()
    total_reviews = serializers.ReadOnlyField()

    class Meta:
        model = Service
        fields = ['id', 'provider', 'category', 'title', 'description',
                 'price', 'credits_required', 'duration_minutes', 'images',
                 'average_rating', 'total_reviews', 'is_active',
                 'created_at', 'updated_at']
        read_only_fields = ['provider', 'created_at', 'updated_at']


class ServiceCreateUpdateSerializer(serializers.ModelSerializer):
    images = ServiceImageSerializer(many=True, required=False)

    class Meta:
        model = Service
        fields = ['category', 'title', 'description', 'price', 'credits_required',
                 'duration_minutes', 'images', 'is_active']

    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        validated_data['provider'] = self.context['request'].user
        service = Service.objects.create(**validated_data)

        for image_data in images_data:
            ServiceImage.objects.create(service=service, **image_data)

        return service

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update images if provided
        if images_data:
            instance.images.all().delete()
            for image_data in images_data:
                ServiceImage.objects.create(service=instance, **image_data)

        return instance


class BookingSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    service_title = serializers.CharField(source='service.title', read_only=True)
    service_price = serializers.DecimalField(source='service.price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'customer', 'provider', 'service', 'customer_name',
                 'provider_name', 'service_title', 'service_price',
                 'scheduled_date', 'scheduled_time', 'status', 'notes',
                 'total_amount', 'payment_method', 'is_paid',
                 'created_at', 'updated_at']
        read_only_fields = ['customer', 'provider', 'created_at', 'updated_at']

    def create(self, validated_data):
        service = validated_data['service']
        validated_data['customer'] = self.context['request'].user
        validated_data['provider'] = service.provider
        validated_data['total_amount'] = service.price
        return super().create(validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    service_title = serializers.CharField(source='service.title', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'booking', 'service', 'customer', 'provider',
                 'customer_name', 'service_title', 'rating', 'comment',
                 'provider_response', 'created_at', 'updated_at']
        read_only_fields = ['customer', 'provider', 'service', 'created_at', 'updated_at']

    def create(self, validated_data):
        booking = validated_data['booking']
        validated_data['customer'] = booking.customer
        validated_data['provider'] = booking.provider
        validated_data['service'] = booking.service
        return super().create(validated_data)


class ProviderDashboardSerializer(serializers.ModelSerializer):
    total_services = serializers.SerializerMethodField()
    active_services = serializers.SerializerMethodField()
    pending_bookings = serializers.SerializerMethodField()
    completed_bookings = serializers.SerializerMethodField()
    this_month_earnings = serializers.SerializerMethodField()

    class Meta:
        model = ProviderProfile
        fields = ['rating', 'total_earnings', 'jobs_completed', 'total_services',
                 'active_services', 'pending_bookings', 'completed_bookings',
                 'this_month_earnings']

    def get_total_services(self, obj):
        return obj.user.services.count()

    def get_active_services(self, obj):
        return obj.user.services.filter(is_active=True).count()

    def get_pending_bookings(self, obj):
        return obj.user.provider_bookings.filter(status='pending').count()

    def get_completed_bookings(self, obj):
        return obj.user.provider_bookings.filter(status='completed').count()

    def get_this_month_earnings(self, obj):
        from django.utils import timezone
        from datetime import datetime
        current_month = timezone.now().month
        current_year = timezone.now().year

        monthly_bookings = obj.user.provider_bookings.filter(
            status='completed',
            created_at__month=current_month,
            created_at__year=current_year
        )
        return sum(booking.total_amount for booking in monthly_bookings)


class InstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Installment
        fields = ['id', 'installment_number', 'amount', 'due_date', 'paid_date',
                 'status', 'transaction_id', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class PaymentSerializer(serializers.ModelSerializer):
    installments = InstallmentSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='user.name', read_only=True)
    booking_details = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ['id', 'booking', 'user', 'customer_name', 'amount', 'payment_type',
                 'payment_method', 'status', 'transaction_id', 'gateway_response',
                 'installments', 'booking_details', 'created_at', 'updated_at']
        read_only_fields = ['user', 'status', 'transaction_id', 'created_at', 'updated_at']

    def get_booking_details(self, obj):
        return {
            'id': obj.booking.id,
            'service_title': obj.booking.service.title,
            'scheduled_date': obj.booking.scheduled_date,
            'scheduled_time': obj.booking.scheduled_time
        }

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PaymentProcessSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    payment_type = serializers.ChoiceField(choices=Payment.PAYMENT_TYPE)
    payment_method = serializers.ChoiceField(choices=Booking.PAYMENT_METHODS)
    installment_count = serializers.IntegerField(required=False, min_value=2, max_value=12)
    card_token = serializers.CharField(required=False, allow_blank=True)


class UserCreditsSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = UserCredits
        fields = ['id', 'user', 'user_name', 'amount', 'transaction_type',
                 'description', 'booking', 'balance_after', 'created_at']
        read_only_fields = ['user', 'balance_after', 'created_at']


class UserCreditsBalanceSerializer(serializers.Serializer):
    total_credits = serializers.IntegerField()
    recent_transactions = UserCreditsSerializer(many=True, read_only=True)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'user', 'address_type', 'street_address', 'city', 'state',
                 'postal_code', 'country', 'latitude', 'longitude', 'is_default',
                 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user

        # If this is set as default, unset other defaults
        if validated_data.get('is_default', False):
            Address.objects.filter(user=validated_data['user'], is_default=True).update(is_default=False)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # If this is set as default, unset other defaults
        if validated_data.get('is_default', False):
            Address.objects.filter(user=instance.user, is_default=True).exclude(id=instance.id).update(is_default=False)

        return super().update(instance, validated_data)


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.name', read_only=True)
    sender_profile_image = serializers.CharField(source='sender.profile_image_url', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_name', 'sender_profile_image',
                 'content', 'media_url', 'is_read', 'created_at']
        read_only_fields = ['sender', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    customer_profile_image = serializers.CharField(source='customer.profile_image_url', read_only=True)
    provider_profile_image = serializers.CharField(source='provider.profile_image_url', read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'customer', 'provider', 'customer_name', 'provider_name',
                 'customer_profile_image', 'provider_profile_image', 'booking',
                 'last_message', 'unread_count', 'last_message_at', 'created_at']
        read_only_fields = ['created_at', 'last_message_at']

    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None

    def get_unread_count(self, obj):
        user = self.context.get('request').user
        return obj.messages.exclude(sender=user).filter(is_read=False).count()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'notification_type', 'title', 'message',
                 'booking', 'is_read', 'created_at']
        read_only_fields = ['user', 'created_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['id', 'user', 'email_notifications', 'sms_notifications',
                 'push_notifications', 'booking_updates', 'payment_updates',
                 'new_messages', 'marketing_emails', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']


class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDevice
        fields = ['id', 'user', 'device_token', 'device_type', 'device_name',
                 'is_active', 'created_at', 'updated_at', 'last_used']
        read_only_fields = ['user', 'created_at', 'updated_at', 'last_used']

    def create(self, validated_data):
        # Get or update existing device token
        device_token = validated_data.get('device_token')
        user = validated_data.get('user')

        device, created = FCMDevice.objects.update_or_create(
            device_token=device_token,
            defaults={
                'user': user,
                'device_type': validated_data.get('device_type'),
                'device_name': validated_data.get('device_name', ''),
                'is_active': True
            }
        )
        return device