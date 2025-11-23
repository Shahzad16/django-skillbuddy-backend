"""
Custom exception handler for Django REST Framework.

This module provides a standardized error response format for all API endpoints.
All errors are formatted consistently to ensure the Flutter app can reliably
parse and display appropriate error messages to users.

Standard error response format:
{
    "success": false,
    "message": "Human-readable error message",
    "errors": {
        "field_name": ["Error message 1", "Error message 2"],
        "non_field_errors": ["General error"]
    }
}
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError


def custom_exception_handler(exc, context):
    """
    Custom exception handler that formats all errors consistently.

    Args:
        exc: The exception that was raised
        context: Context information about where the exception occurred

    Returns:
        Response: Standardized error response
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    # If DRF handled it, format the response
    if response is not None:
        custom_response = format_error_response(response.data, response.status_code)
        return Response(custom_response, status=response.status_code)

    # Handle unhandled exceptions (500 errors)
    return Response(
        {
            'success': False,
            'message': 'Internal server error',
            'errors': {
                'non_field_errors': ['An unexpected error occurred. Please try again later.']
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def format_error_response(error_data, status_code):
    """
    Format error data into standard format.

    Args:
        error_data: Error data from DRF exception handler
        status_code: HTTP status code

    Returns:
        dict: Formatted error response
    """
    # Handle DRF validation errors
    if isinstance(error_data, dict):
        # Check if it's already in our format
        if 'success' in error_data:
            return error_data

        # Handle DRF's detail field (authentication errors, etc.)
        if 'detail' in error_data:
            # Check if it's a complex detail with code and messages (JWT errors)
            if isinstance(error_data['detail'], dict):
                return {
                    'success': False,
                    'message': str(error_data['detail'].get('detail', 'An error occurred')),
                    'errors': {
                        'non_field_errors': [str(error_data['detail'].get('detail', 'An error occurred'))]
                    }
                }
            else:
                return {
                    'success': False,
                    'message': str(error_data['detail']),
                    'errors': {
                        'non_field_errors': [str(error_data['detail'])]
                    }
                }

        # Handle validation errors
        formatted_errors = {}
        for field, errors in error_data.items():
            if isinstance(errors, list):
                formatted_errors[field] = [str(e) for e in errors]
            else:
                formatted_errors[field] = [str(errors)]

        # Get appropriate message based on status code
        message = get_error_message(status_code)

        return {
            'success': False,
            'message': message,
            'errors': formatted_errors
        }

    # Handle string errors
    elif isinstance(error_data, str):
        return {
            'success': False,
            'message': error_data,
            'errors': {
                'non_field_errors': [error_data]
            }
        }

    # Handle list errors
    elif isinstance(error_data, list):
        return {
            'success': False,
            'message': 'Validation error',
            'errors': {
                'non_field_errors': [str(e) for e in error_data]
            }
        }

    # Fallback
    return {
        'success': False,
        'message': 'An error occurred',
        'errors': {
            'non_field_errors': ['Unknown error']
        }
    }


def get_error_message(status_code):
    """
    Get appropriate error message based on status code.

    Args:
        status_code: HTTP status code

    Returns:
        str: User-friendly error message
    """
    messages = {
        400: 'Bad request - please check your input',
        401: 'Authentication required',
        403: 'You do not have permission to perform this action',
        404: 'Resource not found',
        409: 'Resource conflict',
        422: 'Unable to process request',
        429: 'Too many requests - please try again later',
        500: 'Internal server error',
        503: 'Service temporarily unavailable'
    }
    return messages.get(status_code, 'An error occurred')
