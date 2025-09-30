from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import (
    ServiceCategory, ProviderProfile, Service, ServiceImage,
    Booking, Review, Payment, Installment, UserCredits, Address
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
