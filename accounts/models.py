from django.contrib.auth.models import AbstractUser
from django.db import models
import random
import string


class User(AbstractUser):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_image_url = models.URLField(blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def save(self, *args, **kwargs):
        if not self.name and (self.first_name or self.last_name):
            self.name = f"{self.first_name} {self.last_name}".strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class EmailVerificationToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def generate_token(self):
        self.token = ''.join(random.choices(string.digits, k=6))

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class PhoneVerificationToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def generate_token(self):
        self.token = ''.join(random.choices(string.digits, k=6))

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def generate_token(self):
        import uuid
        self.token = str(uuid.uuid4()).replace('-', '')

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
