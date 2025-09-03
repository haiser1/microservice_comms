# Microservice Comms Library

A shared Python library designed to standardize and simplify communication between microservices. It provides a resilient HTTP client with built-in features like HMAC authentication, automatic retries, and a circuit breaker pattern.

---

## Features

- **HMAC Authentication**: Securely sign internal requests using HMAC-SHA256.
- **Resilient HTTP Client**: Built on `requests` with a shared session for connection pooling.
- **Automatic Retries**: Automatically retries failed requests (e.g., `5xx` status codes) with a configurable backoff strategy.
- **Circuit Breaker**: Prevents the application from repeatedly trying to execute an operation that is likely to fail. After a set number of failures, the breaker trips and subsequent calls fail instantly for a configured timeout period.
- **Centralized Error Handling**: Provides a consistent set of custom exceptions for common HTTP errors (`404 Not Found`, `400 Bad Request`, etc.).

---

## Installation

add `microservice_comms @ git+ssh://git@github.com:haiser1/microservice_comms.git@v0.1.0` to your requirements.txt file and install the library using `pip install -r requirements.txt`.
