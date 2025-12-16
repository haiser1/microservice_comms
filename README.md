# Microservice Comms Library

A shared Python library designed to standardize and simplify communication between microservices. It provides a resilient HTTP client with built-in features like HMAC authentication, automatic retries, parallel bulk requests, and a circuit breaker pattern.

---

## Features

- **HMAC Authentication**: Securely sign internal requests using HMAC-SHA256.
- **Resilient HTTP Client**: Built on `requests` with a shared session for connection pooling.
- **Parallel Bulk Requests**: Efficiently send multiple requests in parallel using native `gevent` pools without the overhead of extra libraries.
- **Automatic Retries**: Automatically retries failed requests (e.g., `5xx` status codes) with a configurable backoff strategy.
- **Circuit Breaker**: Prevents the application from repeatedly trying to execute an operation that is likely to fail.
- **Centralized Error Handling**: Provides a consistent set of custom exceptions for common HTTP errors (`404 Not Found`, `400 Bad Request`, etc.).
- **Concurrency Safe**: Designed specifically for high-concurrency environments like Gunicorn with `gevent` workers.

---

## Installation

### Option 1: Add to `requirements.txt`

Add the following line to your project's `requirements.txt` file to manage it as a dependency:

```bash
microservice_comms @ git+https://github.com/haiser1/microservice_comms.git@v1.7.2
```

Then, install all dependencies:

```bash
pip install -r requirements.txt
```

_(Note: Remember to replace `v1.7.2` with the latest version tag you want to use.)_

### Option 2: Direct Install

To install it directly from the command line, run this command:

```bash
pip install git+[https://github.com/haiser1/microservice_comms.git@v1.7.2](https://github.com/haiser1/microservice_comms.git@v1.7.2)
```

## Concurrency & gevent Compatibility

This library is native to Gevent. It requires the application to be monkey-patched to work correctly (standard procedure for Flask apps running on Gunicorn + Gevent).

It uses gevent.pool for parallel execution and gevent.local to manage requests.Session objects. This ensures that each greenlet (e.g., a Gunicorn worker processing a request) gets its own isolated HTTP session, preventing race conditions and ensuring connection pool integrity.

## How to Use

### 1. Basic Single Request

First, create a specific client for the service you want to communicate with by inheriting from BaseServiceClient.

```python
# my_service_client.py
from microservice_comms import BaseServiceClient

class MyServiceClient(BaseServiceClient):
    BASE_URL = "[https://my-service.com](https://my-service.com)"
    SERVICE_ID = "my-service-id"
    SECRET = "my-secret-key"

    def get_user(self, user_id):
        # The _execute_request method is inherited and handles auth & errors
        return self._execute_request("GET", f"/users/{user_id}")
```

### 2. Parallel Bulk Requests (New)

You can fetch data from multiple endpoints simultaneously using \_execute_bulk_request.

```python
def get_dashboard_data(self, user_id):
        requests_data = [
            {"method": "GET", "endpoint": f"/users/{user_id}/profile"},
            {"method": "GET", "endpoint": f"/users/{user_id}/orders", "params": {"limit": 5}},
            {"method": "GET", "endpoint": f"/users/{user_id}/notifications"}
        ]

        # Returns a list of Response objects (or Exceptions) in the exact same order
        responses = self._execute_bulk_request(requests_data)

        profile = responses[0]
        orders = responses[1]
        notifications = responses[2]

        return {
            "profile": profile.json() if profile.status_code == 200 else None,
            "orders": orders.json() if orders.status_code == 200 else [],
            # ... handle others
        }
```

### 3. Handling Exceptions

Use the specific exceptions provided by the library to handle errors gracefully.

```python
# main.py
from my_service_client import MyServiceClient
from microservice_comms import InternalServiceError, NotFound, BadRequest, ServiceError

client = MyServiceClient()

try:
    response = client.get_user("123")
    user_data = response.json()
    print(user_data)
except NotFound:
    print("User with ID 123 was not found.")
except InternalServiceError as e:
    print(f"A network or service connectivity error occurred: {e}")
except ServiceError as e:
    print(f"An unexpected error occurred from the service: {e}")
```
