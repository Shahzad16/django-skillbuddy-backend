from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import (
    ServiceCategory, ProviderProfile, Service, ServiceImage,
    Booking, Review, Payment, Installment, UserCredits, Address,
    Conversation, Message, Notification, NotificationPreference, FCMDevice
)


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(ModelAdmin):
    list_display = ('name', 'icon', 'color', 'is_active', 'services_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)

    def services_count(self, obj):
        return obj.services.count()
    services_count.short_description = 'Services Count'


class ServiceImageInline(admin.TabularInline):
    model = ServiceImage
    extra = 1
    readonly_fields = ('created_at',)


@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    list_display = ('title', 'provider_name', 'category', 'price', 'duration_minutes',
                   'is_active', 'average_rating', 'total_bookings', 'created_at')
    list_filter = ('category', 'is_active', 'created_at', 'provider')
    search_fields = ('title', 'description', 'provider__name', 'provider__email')
    ordering = ('-created_at',)
    inlines = [ServiceImageInline]

    def provider_name(self, obj):
        return obj.provider.name or obj.provider.username
    provider_name.short_description = 'Provider'

    def total_bookings(self, obj):
        return obj.bookings.count()
    total_bookings.short_description = 'Total Bookings'


@admin.register(ProviderProfile)
class ProviderProfileAdmin(ModelAdmin):
    list_display = ('user_name', 'account_type', 'rating', 'jobs_completed',
                   'total_earnings', 'is_verified', 'is_available', 'created_at')
    list_filter = ('account_type', 'is_verified', 'is_available', 'created_at')
    search_fields = ('user__name', 'user__email', 'business_name')
    ordering = ('-created_at',)
    filter_horizontal = ('skills',)

    def user_name(self, obj):
        return obj.user.name or obj.user.username
    user_name.short_description = 'User'


@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = ('id', 'customer_name', 'provider_name', 'service_title',
                   'scheduled_date', 'status', 'total_amount', 'is_paid', 'created_at')
    list_filter = ('status', 'payment_method', 'is_paid', 'scheduled_date', 'created_at')
    search_fields = ('customer__name', 'provider__name', 'service__title')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    def customer_name(self, obj):
        return obj.customer.name or obj.customer.username
    customer_name.short_description = 'Customer'

    def provider_name(self, obj):
        return obj.provider.name or obj.provider.username
    provider_name.short_description = 'Provider'

    def service_title(self, obj):
        return obj.service.title
    service_title.short_description = 'Service'


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ('id', 'customer_name', 'service_title', 'rating',
                   'has_response', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('customer__name', 'service__title', 'comment')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    def customer_name(self, obj):
        return obj.customer.name or obj.customer.username
    customer_name.short_description = 'Customer'

    def service_title(self, obj):
        return obj.service.title
    service_title.short_description = 'Service'

    def has_response(self, obj):
        return bool(obj.provider_response)
    has_response.boolean = True
    has_response.short_description = 'Has Provider Response'


@admin.register(ServiceImage)
class ServiceImageAdmin(ModelAdmin):
    list_display = ('service', 'image_url', 'is_primary', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('service__title', 'alt_text')
    ordering = ('-created_at',)


class InstallmentInline(admin.TabularInline):
    model = Installment
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ('id', 'user_name', 'booking_id', 'amount', 'payment_type',
                   'payment_method', 'status', 'transaction_id', 'created_at')
    list_filter = ('payment_type', 'payment_method', 'status', 'created_at')
    search_fields = ('user__name', 'user__email', 'transaction_id', 'booking__id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [InstallmentInline]

    def user_name(self, obj):
        return obj.user.name or obj.user.username
    user_name.short_description = 'User'

    def booking_id(self, obj):
        return f"#{obj.booking.id}"
    booking_id.short_description = 'Booking'


@admin.register(Installment)
class InstallmentAdmin(ModelAdmin):
    list_display = ('payment_id', 'installment_number', 'amount', 'due_date',
                   'paid_date', 'status', 'created_at')
    list_filter = ('status', 'due_date', 'created_at')
    search_fields = ('payment__booking__id', 'transaction_id')
    ordering = ('payment', 'installment_number')
    readonly_fields = ('created_at', 'updated_at')

    def payment_id(self, obj):
        return f"Payment #{obj.payment.id}"
    payment_id.short_description = 'Payment'


@admin.register(UserCredits)
class UserCreditsAdmin(ModelAdmin):
    list_display = ('id', 'user_name', 'amount', 'transaction_type', 'description',
                   'balance_after', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('user__name', 'user__email', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

    def user_name(self, obj):
        return obj.user.name or obj.user.username
    user_name.short_description = 'User'


@admin.register(Address)
class AddressAdmin(ModelAdmin):
    list_display = ('id', 'user_name', 'address_type', 'city', 'country',
                   'is_default', 'created_at')
    list_filter = ('address_type', 'is_default', 'country', 'created_at')
    search_fields = ('user__name', 'user__email', 'street_address', 'city', 'postal_code')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    def user_name(self, obj):
        return obj.user.name or obj.user.username
    user_name.short_description = 'User'


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'created_at')
    fields = ('sender', 'content', 'is_read', 'created_at')
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(ModelAdmin):
    list_display = ('id', 'customer_name', 'provider_name', 'booking_id',
                   'message_count', 'last_message_at', 'created_at')
    list_filter = ('created_at', 'last_message_at')
    search_fields = ('customer__name', 'provider__name', 'booking__id')
    ordering = ('-last_message_at',)
    readonly_fields = ('created_at', 'updated_at', 'last_message_at')
    inlines = [MessageInline]

    def customer_name(self, obj):
        return obj.customer.name or obj.customer.username
    customer_name.short_description = 'Customer'

    def provider_name(self, obj):
        return obj.provider.name or obj.provider.username
    provider_name.short_description = 'Provider'

    def booking_id(self, obj):
        return f"#{obj.booking.id}" if obj.booking else "N/A"
    booking_id.short_description = 'Booking'

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'


@admin.register(Message)
class MessageAdmin(ModelAdmin):
    list_display = ('id', 'conversation_id', 'sender_name', 'content_preview',
                   'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__name', 'content', 'conversation__id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

    def conversation_id(self, obj):
        return f"Conversation #{obj.conversation.id}"
    conversation_id.short_description = 'Conversation'

    def sender_name(self, obj):
        return obj.sender.name or obj.sender.username
    sender_name.short_description = 'Sender'

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ('id', 'user_name', 'notification_type', 'title',
                   'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__name', 'user__email', 'title', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

    def user_name(self, obj):
        return obj.user.name or obj.user.username
    user_name.short_description = 'User'

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected notifications as read"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = "Mark selected notifications as unread"


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(ModelAdmin):
    list_display = ('user_name', 'email_notifications', 'sms_notifications',
                   'push_notifications', 'booking_updates', 'payment_updates',
                   'new_messages', 'created_at')
    list_filter = ('email_notifications', 'sms_notifications', 'push_notifications',
                  'booking_updates', 'payment_updates', 'new_messages')
    search_fields = ('user__name', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    def user_name(self, obj):
        return obj.user.name or obj.user.username
    user_name.short_description = 'User'


@admin.register(FCMDevice)
class FCMDeviceAdmin(ModelAdmin):
    list_display = ('id', 'user_name', 'device_type', 'device_name', 'is_active',
                   'token_preview', 'last_used', 'created_at')
    list_filter = ('device_type', 'is_active', 'created_at', 'last_used')
    search_fields = ('user__name', 'user__email', 'device_token', 'device_name')
    ordering = ('-last_used',)
    readonly_fields = ('created_at', 'updated_at', 'last_used')

    def user_name(self, obj):
        return obj.user.name or obj.user.username
    user_name.short_description = 'User'

    def token_preview(self, obj):
        return f"{obj.device_token[:30]}..." if len(obj.device_token) > 30 else obj.device_token
    token_preview.short_description = 'Token'

    actions = ['activate_devices', 'deactivate_devices']

    def activate_devices(self, request, queryset):
        queryset.update(is_active=True)
    activate_devices.short_description = "Activate selected devices"

    def deactivate_devices(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_devices.short_description = "Deactivate selected devices"
