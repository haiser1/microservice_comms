# Microservice Comms Library

A shared Python library designed to standardize and simplify communication between microservices. It provides a resilient HTTP client with built-in features like HMAC authentication, automatic retries, and a circuit breaker pattern.

---

## Features

- **HMAC Authentication**: Securely sign internal requests using HMAC-SHA256.
- **Resilient HTTP Client**: Built on `requests` with a shared session for connection pooling.
- **Automatic Retries**: Automatically retries failed requests (e.g., `5xx` status codes) with a configurable backoff strategy.
- **Circuit Breaker**: Prevents the application from repeatedly trying to execute an operation that is likely to fail. After a set number of failures, the breaker trips and subsequent calls fail instantly for a configured timeout period.
- **Centralized Error Handling**: Provides a consistent set of custom exceptions for common HTTP errors (`404 Not Found`, `400 Bad Request`, etc.).
- **Concurrency Safe**: Designed for high-concurrency environments like Gunicorn with `gevent` workers, ensuring thread and greenlet safety for HTTP sessions.

---

## Installation

### Option 1: Add to `requirements.txt`

Add the following line to your project's `requirements.txt` file to manage it as a dependency:

`microservice_comms @ git+https://github.com/haiser1/microservice_comms.git@v1.4.1`

Then, install all dependencies:

```bash
pip install -r requirements.txt
```

_(Note: Remember to replace `v1.3.1` with the latest version tag you want to use.)_

### Option 2: Direct Install

To install it directly from the command line, run this command:

```bash
pip install git+[https://github.com/haiser1/microservice_comms.git@v1.4.1](https://github.com/haiser1/microservice_comms.git@v1.3.1)
```

## Concurrency & gevent Compatibility

This library is designed to be thread-safe and greenlet-safe, making it suitable for high-concurrency applications.

It internally uses gevent.local to manage requests.Session objects. This ensures that each greenlet (e.g., a Gunicorn worker) gets its own isolated HTTP session, preventing race conditions and ensuring connection pool integrity.

While optimized for gevent, the library does not require it and will function correctly in standard multi-threaded or multi-process environments.

## How to Use

First, create a specific client for the service you want to communicate with by inheriting from BaseServiceClient.

```python
# my_service_client.py
from microservice_comms import BaseServiceClient

class MyServiceClient(BaseServiceClient):
    BASE_URL = "[https://my-service.com](https://my-service.com)"
    SERVICE_ID = "my-service-id"
    SECRET = "my-secret-key"

    def get_user(self, user_id):
        # The _execute_request method is inherited and handles all the magic
        return self._execute_request("GET", f"/users/{user_id}")
```

Then, use your new client in your application and handle the specific exceptions provided by the library.

```python
# main.py
from my_service_client import MyServiceClient
# Import exceptions directly from the library
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
