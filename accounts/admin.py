from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from .models import User, EmailVerificationToken, PhoneVerificationToken, PasswordResetToken


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ('email', 'username', 'name', 'is_email_verified', 'is_phone_verified', 'is_staff', 'created_at')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_email_verified', 'is_phone_verified', 'created_at')
    search_fields = ('username', 'email', 'name', 'first_name', 'last_name')
    ordering = ('-created_at',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('name', 'phone_number', 'profile_image_url', 'is_email_verified', 'is_phone_verified')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_login_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'last_login_at')


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'expires_at', 'is_expired')
    list_filter = ('created_at', 'expires_at')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('created_at',)

    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'


@admin.register(PhoneVerificationToken)
class PhoneVerificationTokenAdmin(ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'expires_at', 'is_expired')
    list_filter = ('created_at', 'expires_at')
    search_fields = ('user__email', 'user__phone_number')
    readonly_fields = ('created_at',)

    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(ModelAdmin):
    list_display = ('user', 'token', 'is_used', 'created_at', 'expires_at', 'is_expired')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('created_at', 'token')

    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'
