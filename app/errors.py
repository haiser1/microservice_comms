"""
This module provides custom exceptions for handling errors in the application.
"""


class InternalServiceError(Exception):
    """Exception raised when an internal service call fails after all retries."""

    def __init__(self, message, *args):
        self.message = message
        super().__init__(self.message, *args)


class ServiceClientError(Exception):
    """Base exception for all error from service client"""

    pass


class NotFound(ServiceClientError):
    """Exception raised when response status code is 404."""

    pass


class BadRequest(ServiceClientError):
    """Exception raised when response status code is 400."""

    pass


class ServiceError(ServiceClientError):
    """Exception raised when response status code is 500."""

    pass
