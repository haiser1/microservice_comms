"""
This module provides a base client class for making requests to internal services.
"""

import logging

import grequests
import requests

from .auth import generate_api_key_header, generate_internal_headers
from .errors import BadRequest, InternalServiceError, NotFound, ServiceError
from .http_session import get_session

logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 10


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


def send_bulk_internal_requests(
    requests_data: list, service_id: str, secret: str, default_timeout=DEFAULT_TIMEOUT
):
    """
    Sends multiple internal requests in parallel using grequests.

    Args:
        requests_data (list): A list of dictionaries, where each dict contains
                              details for a single request (e.g., 'method', 'url', 'json').
        service_id (str): The service ID for authentication.
        secret (str): The secret key for authentication.
        default_timeout (int): The timeout for each request.

    Returns:
        list: A list of `requests.Response` objects or None for failed requests.
    """
    prepared_requests = []
    sessions = {}

    for req_data in requests_data:
        try:
            method = req_data.get("method", "GET").upper()
            url = req_data["url"]
            kwargs = req_data.copy()

            kwargs.pop("method", None)
            kwargs.pop("url", None)

            headers = kwargs.pop("headers", {})
            need_hmac = kwargs.pop("need_hmac_header", True)
            timeout = kwargs.pop("timeout", default_timeout)

            if need_hmac:
                auth_headers = generate_internal_headers(
                    method, url, service_id, secret
                )
            else:
                auth_headers = generate_api_key_header(secret, service_id)
            headers.update(auth_headers)

            host = url.split("/")[2]
            if host not in sessions:
                sessions[host] = get_session(url)
            session = sessions[host]

            req = grequests.AsyncRequest(
                method, url, headers=headers, session=session, timeout=timeout, **kwargs
            )
            prepared_requests.append(req)

        except Exception as e:
            logger.error(
                f"Failed to prepare bulk request for data {req_data}. Error: {e}",
                exc_info=True,
            )

    if not prepared_requests:
        return []

    def exception_handler(request, exception):
        logger.error(f"Bulk request to {request.url} failed: {exception}")

    return grequests.map(prepared_requests, exception_handler=exception_handler)


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
                try:
                    error_message = response.json().get("message", "Bad Request")
                    raise BadRequest(f"{error_message}")
                except ValueError:
                    error_message = f"Bad Request at {full_url} with non-JSON response. {response.text}"
                    raise BadRequest(error_message)

            elif response.status_code == 404:
                try:
                    error_message = response.json().get(
                        "message", "Resource not found."
                    )
                    raise NotFound(f"{error_message}")
                except ValueError:
                    error_message = f"Resource not found at {full_url} with non-JSON response. {response.text}"
                    raise NotFound(error_message)
            else:
                raise ServiceError(
                    f"Service returned an unexpected status {response.status_code} at {full_url}: {response.text}"
                )

        except InternalServiceError as e:
            logger.error(f"A critical connectivity error occurred with {full_url}: {e}")
            raise

    @classmethod
    def _execute_bulk_request(cls, requests_data: list) -> list:
        """
        Executes a bulk request and handles standard response logic.

        Args:
            requests_data (list): A list of dictionaries containing the request data.

        Returns:
            list: A list of responses from the bulk request.
        """
        if not all([cls.BASE_URL, cls.SERVICE_ID, cls.SECRET]):
            raise NotImplementedError("BASE_URL, SERVICE_ID, and SECRET must be set.")

        # Siapkan data lengkap untuk fungsi send_bulk_internal_requests
        processed_data = []
        for req in requests_data:
            full_url = f"{cls.BASE_URL.rstrip('/')}/{req['endpoint'].lstrip('/')}"
            new_req = req.copy()
            new_req["url"] = full_url
            processed_data.append(new_req)

        raw_responses = send_bulk_internal_requests(
            processed_data,
            service_id=cls.SERVICE_ID,
            secret=cls.SECRET,
        )

        # Process responses
        processed_results = []
        for i, res in enumerate(raw_responses):
            if res is None:
                # if res is None, it means the request failed
                original_url = processed_data[i]["url"]
                processed_results.append(
                    InternalServiceError(
                        f"Request failed to connect for URL: {original_url}"
                    )
                )
                continue

            if 200 <= res.status_code < 300:
                processed_results.append(res)
            elif res.status_code == 400:
                msg = cls._parse_error_response(res, "Bad Request")
                processed_results.append(BadRequest(msg))
            elif res.status_code == 404:
                msg = cls._parse_error_response(res, "Resource not found")
                processed_results.append(NotFound(msg))
            else:
                # unexpected example is 500
                processed_results.append(
                    ServiceError(
                        f"Unexpected status {res.status_code} for URL: {res.request.url}"
                    )
                )

        return processed_results

    @staticmethod
    def _parse_error_response(response: requests.Response, default_message: str) -> str:
        """
        Parses the error message from a response.

        Args:
            response (requests.Response): The response to parse.
            default_message (str): The default error message to use if the response cannot be parsed.

        Returns:
            str: The parsed error message.
        """
        try:
            return response.json().get("message", default_message)
        except ValueError:
            return (
                f"{default_message} URL: {response.request.url} | Body: {response.text}"
            )
