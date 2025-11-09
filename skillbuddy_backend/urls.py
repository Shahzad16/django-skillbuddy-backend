"""
URL configuration for skillbuddy_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from datetime import datetime
import platform


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint for CI/CD testing and monitoring.
    Returns server status, deployment time, and system information.
    This endpoint is publicly accessible (no authentication required).
    """
    return Response({
        'status': 'healthy',
        'message': 'SkillBuddy Backend API is running successfully!',
        'timestamp': datetime.now().isoformat(),
        'deployment_info': {
            'branch': 'stagging',
            'environment': 'production',
            'server': platform.node(),
            'python_version': platform.python_version(),
        },
        'cicd_test': 'CI/CD Pipeline Working! ✅'
    })


urlpatterns = [
    path('admin/', admin.site.urls),

    # Health check endpoint
    path('health/', health_check, name='health_check'),
    path('', health_check, name='root'),  # Root endpoint also shows health check

    # API endpoints
    path('auth/', include('accounts.urls')),
    path('api/services/', include('services.urls')),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
