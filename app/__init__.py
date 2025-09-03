from .client import send_internal_request
from .errors import (
    BadRequest,
    InternalServiceError,
    NotFound,
    ServiceClientError,
    ServiceError,
)

__version__ = "0.1.0"

__all__ = [
    "send_internal_request",
    "InternalServiceError",
    "ServiceClientError",
    "NotFound",
    "BadRequest",
    "ServiceError",
]
