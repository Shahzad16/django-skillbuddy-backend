"""
Response utility functions for Django REST Framework.

This module provides helper functions to create standardized success and error
responses across all API endpoints. This ensures consistent response format
that the Flutter app can reliably parse.

Standard success response format:
{
    "success": true,
    "message": "Human-readable success message",
    "data": {...}
}
"""

from rest_framework.response import Response
from rest_framework import status


def success_response(message, data=None, status_code=status.HTTP_200_OK):
    """
    Create a standardized success response.

    Args:
        message (str): Success message to display to the user
        data (dict|list): Response data (optional)
        status_code (int): HTTP status code (default: 200)

    Returns:
        Response: DRF Response object with standardized format

    Examples:
        # Simple success message
        return success_response("User created successfully")

        # Success with data
        return success_response(
            "User created successfully",
            data={'user': user_data},
            status_code=status.HTTP_201_CREATED
        )
    """
    response_data = {
        'success': True,
        'message': message
    }

    if data is not None:
        response_data['data'] = data

    return Response(response_data, status=status_code)


def error_response(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Create a standardized error response.

    Args:
        message (str): Error message to display to the user
        errors (dict): Field-specific errors (optional)
        status_code (int): HTTP status code (default: 400)

    Returns:
        Response: DRF Response object with standardized format

    Examples:
        # Simple error
        return error_response(
            "Invalid booking time",
            status_code=status.HTTP_400_BAD_REQUEST
        )

        # Error with field-specific details
        return error_response(
            "Validation failed",
            errors={
                'email': ['Email is already registered'],
                'password': ['Password is too weak']
            }
        )
    """
    response_data = {
        'success': False,
        'message': message,
    }

    if errors is None:
        errors = {'non_field_errors': [message]}

    response_data['errors'] = errors

    return Response(response_data, status=status_code)


def paginated_response(message, queryset, serializer_class, request):
    """
    Create a standardized paginated response.

    This function handles pagination automatically using DRF's PageNumberPagination
    and wraps the result in the standard response format.

    Args:
        message (str): Success message
        queryset: Django queryset to paginate
        serializer_class: Serializer class to use for data
        request: Django request object (needed for pagination)

    Returns:
        Response: DRF Response object with paginated data

    Example:
        return paginated_response(
            "Services retrieved successfully",
            Service.objects.filter(is_active=True),
            ServiceSerializer,
            request
        )

        Response format:
        {
            "success": true,
            "message": "Services retrieved successfully",
            "data": {
                "count": 100,
                "next": "http://api.example.com/?page=2",
                "previous": null,
                "results": [...]
            }
        }
    """
    from rest_framework.pagination import PageNumberPagination

    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(queryset, request)

    if page is not None:
        serializer = serializer_class(page, many=True)
        paginated_data = paginator.get_paginated_response(serializer.data).data

        return Response({
            'success': True,
            'message': message,
            'data': paginated_data
        })

    # No pagination needed (queryset is small)
    serializer = serializer_class(queryset, many=True)
    return success_response(message, serializer.data)


def validation_error_response(serializer):
    """
    Create a validation error response from serializer errors.

    This is a convenience function to convert DRF serializer errors
    into the standard error format.

    Args:
        serializer: DRF serializer with validation errors

    Returns:
        Response: DRF Response object with validation errors

    Example:
        serializer = UserSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer)
    """
    return error_response(
        message='Validation failed',
        errors=serializer.errors,
        status_code=status.HTTP_400_BAD_REQUEST
    )
