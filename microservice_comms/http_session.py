import functools
import logging
from collections import defaultdict

import pybreaker
import requests
from gevent.local import local
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = (3, 10)  # connect, read
DEFAULT_MAX_RETRY = 3
DEFAULT_FAIL_MAX = 5
DEFAULT_RESET_TIMEOUT = 60

_local = local()
_breakers = defaultdict(
    lambda: pybreaker.CircuitBreaker(
        fail_max=DEFAULT_FAIL_MAX, reset_timeout=DEFAULT_RESET_TIMEOUT
    )
)


class BreakerAdapter(HTTPAdapter):
    def __init__(self, host, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host = host

    def send(self, request, **kwargs):
        host = request.url.split("/")[2]
        breaker = _breakers[host]
        return breaker.call(super().send, request, **kwargs)


def create_session(base_url: str):
    """
    Creates a requests session object with a default timeout and a CircuitBreaker-protected adapter.

    The session is configured to retry up to DEFAULT_MAX_RETRY times with a backoff of 1 second.
    The following status codes are considered failed attempts:
    - 429 (Too Many Requests)
    - 500 (Internal Server Error)
    - 502 (Bad Gateway)
    - 503 (Service Unavailable)
    - 504 (Gateway Timeout)

    The session is also configured to use a CircuitBreaker with:
    - DEFAULT_FAIL_MAX failures before breaking the circuit
    - DEFAULT_RESET_TIMEOUT seconds before resetting the circuit

    :param base_url: The base URL of the service to connect to.
    :return: A requests session object.
    """
    retry_strategy = Retry(
        total=DEFAULT_MAX_RETRY,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    )

    host = base_url.split("/")[2]
    adapter = BreakerAdapter(
        host, max_retries=retry_strategy, pool_connections=50, pool_maxsize=50
    )

    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # enforce default timeout
    original_request = session.request
    session.request = functools.partial(original_request, timeout=DEFAULT_TIMEOUT)
    return session


def get_session(base_url: str) -> requests.Session:
    """
    Returns a requests session object for the given base_url.

    The session will be persisted for the lifetime of the current greenlet.
    If the session does not exist yet, it will be created with a default timeout
    and a CircuitBreaker-protected adapter.

    :param base_url: The base URL of the service to connect to.
    :return: A requests session object.
    """
    if not hasattr(_local, "sessions"):
        _local.sessions = {}

    host = base_url.split("/")[2]
    if host not in _local.sessions:
        _local.sessions[host] = create_session(base_url)
    return _local.sessions[host]
