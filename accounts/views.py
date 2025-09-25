from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
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
        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    serializer = UserLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = serializer.validated_data['user']
    refresh = RefreshToken.for_user(user)

    return Response({
        'user': UserProfileSerializer(user).data,
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'message': 'Login successful'
    })


@api_view(['POST'])
def logout_view(request):
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


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

        return Response({'message': 'Password changed successfully'})


@api_view(['GET'])
def user_list_view(request):
    users = User.objects.all()
    serializer = UserProfileSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_email_verification(request):
    user = request.user
    if user.is_email_verified:
        return Response({'message': 'Email already verified'}, status=status.HTTP_400_BAD_REQUEST)

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
    return Response({
        'message': 'Verification email sent',
        'token': token.token  # Remove this in production
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_email(request):
    user = request.user
    serializer = EmailVerificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        token = EmailVerificationToken.objects.get(user=user)
        if token.is_expired():
            return Response({'error': 'Token expired'}, status=status.HTTP_400_BAD_REQUEST)

        if token.token != serializer.validated_data['token']:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

        user.is_email_verified = True
        user.save()
        token.delete()

        return Response({'message': 'Email verified successfully'})
    except EmailVerificationToken.DoesNotExist:
        return Response({'error': 'No verification token found'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_phone_verification(request):
    user = request.user
    if not user.phone_number:
        return Response({'error': 'No phone number provided'}, status=status.HTTP_400_BAD_REQUEST)

    if user.is_phone_verified:
        return Response({'message': 'Phone already verified'}, status=status.HTTP_400_BAD_REQUEST)

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
    return Response({
        'message': 'Verification SMS sent',
        'token': token.token  # Remove this in production
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_phone(request):
    user = request.user
    serializer = PhoneVerificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        token = PhoneVerificationToken.objects.get(user=user)
        if token.is_expired():
            return Response({'error': 'Token expired'}, status=status.HTTP_400_BAD_REQUEST)

        if token.token != serializer.validated_data['token']:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

        user.is_phone_verified = True
        user.save()
        token.delete()

        return Response({'message': 'Phone verified successfully'})
    except PhoneVerificationToken.DoesNotExist:
        return Response({'error': 'No verification token found'}, status=status.HTTP_400_BAD_REQUEST)


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
    return Response({
        'message': 'Password reset email sent',
        'reset_token': token.token  # Remove this in production
    })


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
            return Response({'error': 'Token expired'}, status=status.HTTP_400_BAD_REQUEST)

        user = token.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        token.is_used = True
        token.save()

        return Response({'message': 'Password reset successfully'})
    except PasswordResetToken.DoesNotExist:
        return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
