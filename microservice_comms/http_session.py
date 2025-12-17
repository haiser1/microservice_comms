import functools
import logging
from collections import defaultdict
from http.cookiejar import CookiePolicy

import pybreaker
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = (3.05, 10)  # (connect, read)
DEFAULT_MAX_RETRY = 3
DEFAULT_FAIL_MAX = 5
DEFAULT_RESET_TIMEOUT = 60

# --- GLOBAL SESSION CACHE ---
# Global session cache
_session_cache = {}

# Circuit Breaker Store
_breakers = defaultdict(
    lambda: pybreaker.CircuitBreaker(
        fail_max=DEFAULT_FAIL_MAX, reset_timeout=DEFAULT_RESET_TIMEOUT
    )
)


# --- BLOCK ALL COOKIES ---
class BlockAllCookies(CookiePolicy):
    return_ok = set_ok = domain_return_ok = path_return_ok = (
        lambda self, *args, **kwargs: False
    )
    netscape = True
    rfc2965 = hide_cookie2 = False


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
    Creates a requests session object for the given base_url.

    The session object is configured with:
    - A retry strategy that retries up to DEFAULT_MAX_RETRY times with a backoff factor of 0.5.
    - A circuit breaker that trips after DEFAULT_FAIL_MAX failures within DEFAULT_RESET_TIMEOUT seconds.
    - A block-all-cookies policy to prevent session leaks between users.
    - A default timeout of DEFAULT_TIMEOUT seconds.

    :param base_url: The base URL of the service.
    :return: A requests session object.
    """
    retry_strategy = Retry(
        total=DEFAULT_MAX_RETRY,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        raise_on_status=False,
    )

    host = base_url.split("/")[2]
    adapter = BreakerAdapter(
        host, max_retries=retry_strategy, pool_connections=20, pool_maxsize=20
    )

    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # SAFETY: BLOCK COOKIES
    session.cookies.set_policy(BlockAllCookies())
    session.auth = None

    # enforce default timeout
    original_request = session.request
    session.request = functools.partial(original_request, timeout=DEFAULT_TIMEOUT)
    return session


def get_session(base_url: str) -> requests.Session:
    """
    Retrieves a requests session object from the global session cache for a given base_url.

    If the given base_url is not found in the global session cache, a new session object
    will be created and stored in the cache.

    Args:
        base_url (str): The base URL of the service to retrieve the session for.

    Returns:
        requests.Session: The session object for the given base_url.
    """
    host = base_url.split("/")[2]

    # Check cache global
    if host not in _session_cache:
        _session_cache[host] = create_session(base_url)

    return _session_cache[host]


def invalidate_session(base_url: str):
    """
    Invalidates and closes a session pool for a given base_url.

    If the given base_url is found in the global session cache, it will be closed
    and removed from the cache. This is useful when encountering connection errors
    to a particular host.

    Args:
        base_url (str): The base URL of the service to invalidate the session for.

    Returns:
        None
    """
    host = base_url.split("/")[2]

    if host in _session_cache:
        logger.warning(
            f"Invalidating and closing session pool for host: {host} due to connection errors."
        )
        try:
            old_session = _session_cache.pop(host)
            old_session.close()
        except Exception as e:
            logger.error(f"Error closing session for {host}: {e}")
