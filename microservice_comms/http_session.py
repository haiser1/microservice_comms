"""
This module provides a shared HTTP session with Circuit Breaker and retry capabilities.
"""

import logging

import pybreaker
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Konfigurasi default, bisa di-override
DEFAULT_FAIL_MAX = 5
DEFAULT_RESET_TIMEOUT = 60
DEFAULT_MAX_RETRY = 3

breaker = pybreaker.CircuitBreaker(
    fail_max=DEFAULT_FAIL_MAX, reset_timeout=DEFAULT_RESET_TIMEOUT
)


class BreakerAdapter(HTTPAdapter):
    """
    Custom HTTP adapter that uses Circuit Breaker for retrying failed requests.
    """

    def send(self, request, **kwargs):
        return breaker.call(super().send, request, **kwargs)


def create_shared_session(
    max_retry=DEFAULT_MAX_RETRY, backoff_factor=1, status_forcelist=None
):
    """
    Create a shared HTTP session with Circuit Breaker and retry capabilities.

    Args:
        max_retry (int): Maximum number of retries. Default is 3.
        backoff_factor (float): Backoff factor for exponential backoff. Default is 1.
        status_forcelist (list): List of status codes to force retry. Default is [429, 500, 502, 503, 504].

    Returns:
        requests.Session: A shared HTTP session with Circuit Breaker and retry capabilities.

    Raises:
        Exception: If there is an error initializing the shared HTTP session.
    """
    if status_forcelist is None:
        status_forcelist = [429, 500, 502, 503, 504]

    try:
        retry_strategy = Retry(
            total=max_retry,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=[
                "HEAD",
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "OPTIONS",
                "PATCH",
            ],
        )
        adapter = BreakerAdapter(max_retries=retry_strategy)

        http_session = requests.Session()
        http_session.mount("http://", adapter)
        http_session.mount("https://", adapter)

        logger.info("HTTP session with Circuit Breaker and retry has been initialized.")
        return http_session
    except Exception as e:
        logger.error(f"Failed to initialize shared HTTP session: {e}", exc_info=True)
        logger.warning(
            "Falling back to a standard HTTP session without retry capabilities."
        )
        return requests.Session()


http_session = create_shared_session()
