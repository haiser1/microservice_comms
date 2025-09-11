import pytest
import requests

from microservice_comms import (
    BadRequest,
    BaseServiceClient,
    InternalServiceError,
    NotFound,
    ServiceError,
)


@pytest.fixture
def service_client():
    """Menyediakan subclass BaseServiceClient untuk testing."""

    class TestClient(BaseServiceClient):
        BASE_URL = "http://test-service.com"
        SERVICE_ID = "test-id"
        SECRET = "test-secret"

    return TestClient


def test_execute_request_success(service_client, requests_mock):
    """Test case untuk request yang berhasil (status 200)."""
    # Langsung daftarkan URL mock ke requests_mock
    endpoint = "/users/123"
    full_url = "http://test-service.com/users/123"
    requests_mock.get(full_url, json={"id": "123"}, status_code=200)

    # Action: Panggil method seperti biasa
    response = service_client._execute_request("GET", endpoint)

    # Assertions
    assert response.status_code == 200
    assert response.json() == {"id": "123"}
    # Verifikasi header dari last_request milik requests_mock
    assert "X-Signature" in requests_mock.last_request.headers


def test_raises_not_found_on_404(service_client, requests_mock):
    """Test untuk exception NotFound saat status 404."""
    full_url = "http://test-service.com/not-found"
    requests_mock.get(full_url, status_code=404)

    with pytest.raises(NotFound):
        service_client._execute_request("GET", "/not-found")


def test_raises_internal_service_error_on_network_failure(
    service_client, requests_mock
):
    """Test untuk exception InternalServiceError saat ada error koneksi."""
    full_url = "http://test-service.com/network-error"
    requests_mock.get(full_url, exc=requests.exceptions.ConnectTimeout)

    with pytest.raises(InternalServiceError):
        service_client._execute_request("GET", "/network-error")


def test_raises_service_error_on_500(service_client, requests_mock):
    """Test untuk exception ServiceError saat status 500."""
    full_url = "http://test-service.com/500-error"
    requests_mock.get(full_url, status_code=500)

    with pytest.raises(ServiceError):
        service_client._execute_request("GET", "/500-error")


def test_raises_bad_request_on_400(service_client, requests_mock):
    """Test untuk exception BadRequest saat status 400."""
    full_url = "http://test-service.com/400-error"
    requests_mock.get(full_url, status_code=400)

    with pytest.raises(BadRequest):
        service_client._execute_request("GET", "/400-error")
