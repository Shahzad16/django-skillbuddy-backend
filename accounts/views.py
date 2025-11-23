from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
from skillbuddy_backend.utils import success_response, error_response
from .models import User, EmailVerificationToken, PhoneVerificationToken, PasswordResetToken
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    PasswordChangeSerializer,
    EmailVerificationSerializer,
    PhoneVerificationSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
)


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return success_response(
            message='User registered successfully',
            data={
                'user': UserProfileSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            status_code=status.HTTP_201_CREATED
        )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    serializer = UserLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = serializer.validated_data['user']
    refresh = RefreshToken.for_user(user)

    return success_response(
        message='Login successful',
        data={
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    )


@api_view(['POST'])
def logout_view(request):
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return success_response(message='Logout successful')
    except Exception:
        return error_response(
            message='Invalid token',
            errors={'refresh': ['Invalid or expired refresh token']},
            status_code=status.HTTP_400_BAD_REQUEST
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class PasswordChangeView(generics.GenericAPIView):
    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return success_response(message='Password changed successfully')


@api_view(['GET'])
def user_list_view(request):
    users = User.objects.all()
    serializer = UserProfileSerializer(users, many=True)
    return success_response(
        message='Users retrieved successfully',
        data=serializer.data
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_email_verification(request):
    user = request.user
    if user.is_email_verified:
        return error_response(
            message='Email already verified',
            errors={'email': ['Email is already verified']},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Delete existing token
    EmailVerificationToken.objects.filter(user=user).delete()

    # Create new token
    token = EmailVerificationToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(hours=1)
    )
    token.generate_token()
    token.save()

    # TODO: Send email with token
    # For now, return the token in response (remove in production)
    return success_response(
        message='Verification email sent',
        data={'token': token.token}  # Remove this in production
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_email(request):
    user = request.user
    serializer = EmailVerificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        token = EmailVerificationToken.objects.get(user=user)
        if token.is_expired():
            return error_response(
                message='Token expired',
                errors={'token': ['Verification token has expired. Please request a new one.']},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if token.token != serializer.validated_data['token']:
            return error_response(
                message='Invalid token',
                errors={'token': ['Invalid verification token']},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        user.is_email_verified = True
        user.save()
        token.delete()

        return success_response(message='Email verified successfully')
    except EmailVerificationToken.DoesNotExist:
        return error_response(
            message='No verification token found',
            errors={'token': ['No verification token found. Please request a new one.']},
            status_code=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_phone_verification(request):
    user = request.user
    if not user.phone_number:
        return error_response(
            message='No phone number provided',
            errors={'phone_number': ['Please add a phone number to your profile first']},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if user.is_phone_verified:
        return error_response(
            message='Phone already verified',
            errors={'phone_number': ['Phone number is already verified']},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Delete existing token
    PhoneVerificationToken.objects.filter(user=user).delete()

    # Create new token
    token = PhoneVerificationToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(minutes=10)
    )
    token.generate_token()
    token.save()

    # TODO: Send SMS with token
    # For now, return the token in response (remove in production)
    return success_response(
        message='Verification SMS sent',
        data={'token': token.token}  # Remove this in production
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_phone(request):
    user = request.user
    serializer = PhoneVerificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        token = PhoneVerificationToken.objects.get(user=user)
        if token.is_expired():
            return error_response(
                message='Token expired',
                errors={'token': ['Verification token has expired. Please request a new one.']},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if token.token != serializer.validated_data['token']:
            return error_response(
                message='Invalid token',
                errors={'token': ['Invalid verification token']},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        user.is_phone_verified = True
        user.save()
        token.delete()

        return success_response(message='Phone verified successfully')
    except PhoneVerificationToken.DoesNotExist:
        return error_response(
            message='No verification token found',
            errors={'token': ['No verification token found. Please request a new one.']},
            status_code=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_request(request):
    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    user = User.objects.get(email=email)

    # Delete existing tokens
    PasswordResetToken.objects.filter(user=user, is_used=False).delete()

    # Create new token
    token = PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(hours=1)
    )
    token.generate_token()
    token.save()

    # TODO: Send email with reset link
    # For now, return the token in response (remove in production)
    return success_response(
        message='Password reset email sent',
        data={'reset_token': token.token}  # Remove this in production
    )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_confirm(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        token = PasswordResetToken.objects.get(
            token=serializer.validated_data['token'],
            is_used=False
        )

        if token.is_expired():
            return error_response(
                message='Token expired',
                errors={'token': ['Password reset token has expired. Please request a new one.']},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        user = token.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        token.is_used = True
        token.save()

        return success_response(message='Password reset successfully')
    except PasswordResetToken.DoesNotExist:
        return error_response(
            message='Invalid or expired token',
            errors={'token': ['Invalid or expired password reset token']},
            status_code=status.HTTP_400_BAD_REQUEST
        )
