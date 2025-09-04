"""
This module provides functions for generating HMAC headers for internal service requests and API Key headers.
"""

import hashlib
import hmac
import time
from urllib.parse import urlparse


def generate_internal_headers(method, url, service_id, secret):
    """Generates HMAC headers for internal service requests."""
    timestamp = str(int(time.time()))
    method = method.upper()
    path = urlparse(url).path

    raw_message = f"{method}|{path}|{timestamp}".encode()
    secret_bytes = secret.encode()
    signature = hmac.new(secret_bytes, raw_message, hashlib.sha256).hexdigest()

    return {
        "X-Service-ID": service_id,
        "X-Timestamp": timestamp,
        "X-Signature": signature,
        "Content-Type": "application/json",
    }


def generate_api_key_header(api_key, service_id):
    """Generates API Key headers."""
    return {
        "X-Service-ID": service_id,
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }
