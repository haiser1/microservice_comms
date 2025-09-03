import logging

import requests

from .auth import generate_api_key_header, generate_internal_headers
from .errors import InternalServiceError
from .http_session import http_session

logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 15  # Definisikan default timeout di sini


def send_internal_request(
    method,
    url,
    service_id,
    secret,
    need_hmac_header=True,
    timeout=DEFAULT_TIMEOUT,
    **kwargs,
):
    """Sends a durable internal HTTP request."""
    headers = kwargs.pop("headers", {})
    try:
        if need_hmac_header:
            auth_headers = generate_internal_headers(method, url, service_id, secret)
        else:
            auth_headers = generate_api_key_header(secret, service_id)

        headers.update(auth_headers)

        response = http_session.request(
            method=method.upper(), url=url, headers=headers, timeout=timeout, **kwargs
        )
        return response

    except requests.exceptions.RequestException as e:
        error_message = (
            f"Failed to connect to {method.upper()} {url} after all retries. Error: {e}"
        )
        logger.error(error_message)
        raise InternalServiceError(error_message) from e
    except ValueError as e:
        logger.error(f"Unsupported HTTP method provided: {method}")
        raise e
