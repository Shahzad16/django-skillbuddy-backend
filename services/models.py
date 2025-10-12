from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, help_text="Icon identifier for Flutter UI")
    color = models.CharField(max_length=7, help_text="Hex color code for Flutter UI")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Service Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class ProviderProfile(models.Model):
    ACCOUNT_TYPES = [
        ('individual', 'Individual'),
        ('business', 'Business'),
        ('company', 'Company'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='provider_profile')
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='individual')
    business_name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    skills = models.ManyToManyField(ServiceCategory, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    jobs_completed = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.name or self.user.username} - {self.account_type}"

    def update_rating(self):
        from .models import Review
        reviews = Review.objects.filter(service__provider=self.user)
        if reviews.exists():
            avg_rating = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.rating = round(avg_rating, 2)
            self.save()


class Service(models.Model):
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='services')
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    credits_required = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(help_text="Service duration in minutes")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.provider.name or self.provider.username}"

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews.exists():
            return reviews.aggregate(models.Avg('rating'))['rating__avg']
        return 0.0

    @property
    def total_reviews(self):
        return self.reviews.count()


class ServiceImage(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField()
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'created_at']

    def __str__(self):
        return f"Image for {self.service.title}"


class Booking(models.Model):
    BOOKING_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHODS = [
        ('card', 'Credit/Debit Card'),
        ('paypal', 'PayPal'),
        ('credits', 'Service Credits'),
        ('cash', 'Cash'),
    ]

    customer = models.ForeignKey(User, related_name='bookings', on_delete=models.CASCADE)
    provider = models.ForeignKey(User, related_name='provider_bookings', on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings')
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='pending')
    notes = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking #{self.id} - {self.service.title}"


class Review(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    provider_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for {self.service.title} - {self.rating} stars"


class Payment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_TYPE = [
        ('immediate', 'Immediate'),
        ('later', 'Pay Later'),
        ('installment', 'Installment'),
        ('credits', 'Credits'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE)
    payment_method = models.CharField(max_length=20, choices=Booking.PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment #{self.id} - {self.amount} ({self.status})"


class Installment(models.Model):
    INSTALLMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='installments')
    installment_number = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=INSTALLMENT_STATUS, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['installment_number']

    def __str__(self):
        return f"Installment {self.installment_number} - {self.amount}"


class UserCredits(models.Model):
    TRANSACTION_TYPE = [
        ('purchase', 'Purchase'),
        ('earned', 'Earned'),
        ('used', 'Used'),
        ('refund', 'Refund'),
        ('bonus', 'Bonus'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_transactions')
    amount = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE)
    description = models.CharField(max_length=200)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    balance_after = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "User Credits"

    def __str__(self):
        return f"{self.user.username} - {self.amount} credits ({self.transaction_type})"


class Address(models.Model):
    ADDRESS_TYPE = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPE, default='home')
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name_plural = "Addresses"

    def __str__(self):
        return f"{self.address_type} - {self.street_address}, {self.city}"


class Conversation(models.Model):
    """Chat conversation between customer and provider"""
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_conversations')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='provider_conversations')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversations')
    last_message_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_message_at']
        unique_together = ['customer', 'provider', 'booking']

    def __str__(self):
        return f"Conversation between {self.customer.name} and {self.provider.name}"


class Message(models.Model):
    """Individual messages in a conversation"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    media_url = models.URLField(blank=True, help_text="URL for image/video attachments")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.name} at {self.created_at}"


class Notification(models.Model):
    """System notifications for users"""
    NOTIFICATION_TYPE = [
        ('booking', 'Booking'),
        ('payment', 'Payment'),
        ('review', 'Review'),
        ('message', 'Message'),
        ('system', 'System'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} notification for {self.user.name}"


class NotificationPreference(models.Model):
    """User notification preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=True)
    booking_updates = models.BooleanField(default=True)
    payment_updates = models.BooleanField(default=True)
    new_messages = models.BooleanField(default=True)
    marketing_emails = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification preferences for {self.user.name}"


class FCMDevice(models.Model):
    """FCM device tokens for push notifications"""
    DEVICE_TYPE = [
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_devices')
    device_token = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPE)
    device_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_used']
        verbose_name = 'FCM Device'
        verbose_name_plural = 'FCM Devices'

    def __str__(self):
        return f"{self.user.name} - {self.device_type} ({self.device_token[:20]}...)"
