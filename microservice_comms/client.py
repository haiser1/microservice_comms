"""
This module provides a base client class for making requests to internal services.
"""

import logging

import requests

from .auth import generate_api_key_header, generate_internal_headers
from .errors import BadRequest, InternalServiceError, NotFound, ServiceError
from .http_session import get_session

logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 15


def send_internal_request(
    method,
    url,
    service_id,
    secret,
    need_hmac_header=True,
    timeout=DEFAULT_TIMEOUT,
    **kwargs,
) -> requests.Response:
    """
    Sends a durable internal HTTP request.

    Args:
        method (str): The HTTP method to use for the request.
        url (str): The URL to make the request to.
        service_id (str): The service ID used for authentication.
        secret (str): The secret used for authentication.
        need_hmac_header (bool, optional): Whether to include HMAC headers. Defaults to True.
        timeout (int, optional): The timeout for the request. Defaults to DEFAULT_TIMEOUT.
        **kwargs: Additional keyword arguments to pass to the requests library.

    Returns:
        requests.Response: The response from the request.

    Raises:
        InternalServiceError: If the request fails after all retries.
    """
    headers = kwargs.pop("headers", {})
    try:
        if need_hmac_header:
            auth_headers = generate_internal_headers(method, url, service_id, secret)
        else:
            auth_headers = generate_api_key_header(secret, service_id)

        headers.update(auth_headers)

        session = get_session(url)
        response = session.request(
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


class BaseServiceClient:
    """
    A base client that handles the boilerplate of making requests and handling responses.

    Attributes:
        BASE_URL (str): The base URL for the service.
        SERVICE_ID (str): The service ID used for authentication.
        SECRET (str): The secret used for authentication.

    Raises:
        NotImplementedError: If BASE_URL, SERVICE_ID, or SECRET is not set in the subclass.

    Methods:
        _execute_request(method, endpoint, **kwargs): Executes the request and handles standard response logic.

    Example:
        class MyServiceClient(BaseServiceClient):
            BASE_URL = "https://my-service.com"
            SERVICE_ID = "my-service-id"
            SECRET = "my-secret-key"

            def get_user(self, user_id):
                return self._execute_request("GET", f"/users/{user_id}")
    """

    BASE_URL = None
    SERVICE_ID = None
    SECRET = None

    @classmethod
    def _execute_request(
        cls, method: str, endpoint: str, need_hmac_header=True, **kwargs
    ) -> requests.Response:
        """
        Executes the request and handles standard response logic.

        Args:
            method (str): The HTTP method to use for the request.
            endpoint (str): The endpoint to make the request to.
            need_hmac_header (bool, optional): Whether to include HMAC headers. Defaults to True.

        Returns:
            requests.Response: The response from the request.
        """
        if not all([cls.BASE_URL, cls.SERVICE_ID, cls.SECRET]):
            raise NotImplementedError(
                "BASE_URL, SERVICE_ID, and SECRET must be set in the subclass."
            )

        full_url = f"{cls.BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"

        try:
            response = send_internal_request(
                method,
                full_url,
                service_id=cls.SERVICE_ID,
                secret=cls.SECRET,
                need_hmac_header=need_hmac_header,
                **kwargs,
            )

            if 200 <= response.status_code < 300:
                return response
            elif response.status_code == 400:
                raise BadRequest(f"Bad request to {full_url}: {response.text}")
            elif response.status_code == 404:
                raise NotFound(f"Resource not found at {full_url}.")
            else:
                raise ServiceError(
                    f"Service returned an unexpected status {response.status_code} at {full_url}: {response.text}"
                )

        except InternalServiceError as e:
            logger.error(f"A critical connectivity error occurred with {full_url}: {e}")
            raise
