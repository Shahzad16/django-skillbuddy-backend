from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentication endpoints (matching Flutter expectations)
    path('signup/', views.UserRegistrationView.as_view(), name='user-signup'),
    path('signin/', views.login_view, name='user-signin'),
    path('signout/', views.logout_view, name='user-signout'),
    path('current-user/', views.UserProfileView.as_view(), name='current-user'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Verification endpoints
    path('send-email-verification/', views.send_email_verification, name='send-email-verification'),
    path('verify-email/', views.verify_email, name='verify-email'),
    path('send-phone-verification/', views.send_phone_verification, name='send-phone-verification'),
    path('verify-phone/', views.verify_phone, name='verify-phone'),

    # Password reset
    path('reset-password/', views.password_reset_request, name='password-reset'),
    path('reset-password/confirm/', views.password_reset_confirm, name='password-reset-confirm'),

    # Profile management
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('password-change/', views.PasswordChangeView.as_view(), name='password-change'),

    # User listing (for admin or internal use)
    path('users/', views.user_list_view, name='user-list'),
]