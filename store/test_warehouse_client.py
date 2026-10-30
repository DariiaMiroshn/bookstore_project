from unittest.mock import Mock, patch
import pytest
from requests.exceptions import RequestException, Timeout

from store.services.warehouse_client import WarehouseClient, WarehouseServiceError


@pytest.fixture
def warehouse_client():
    """Фікстура для створення екземпляра клієнта з тестовими налаштуваннями."""
    return WarehouseClient(base_url="http://test-warehouse:8001", timeout=2.0)


class TestWarehouseClientAuthentication:
    """Тести авторизації клієнта та отримання JWT токена."""

    @patch("store.services.warehouse_client.requests.post")
    def test_authenticate_success(self, mock_post, warehouse_client):
        # Імітуємо успішну відповідь 200 від ендпоінта авторизації
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access": "fake-jwt-access-token"}
        mock_post.return_value = mock_response

        warehouse_client._authenticate()

        assert warehouse_client._access_token == "fake-jwt-access-token"
        headers = warehouse_client._get_headers()
        assert headers["Authorization"] == "Bearer fake-jwt-access-token"

    @patch("store.services.warehouse_client.requests.post")
    def test_authenticate_invalid_credentials_raises_error(self, mock_post, warehouse_client):
        # Імітуємо помилку 401 при невірних облікових даних
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"
        mock_post.return_value = mock_response

        with pytest.raises(WarehouseServiceError, match="Invalid Warehouse credentials"):
            warehouse_client._authenticate()


class TestWarehouseClientOperations:
    """Тести операцій інвентаря зі складом."""

    @patch("store.services.warehouse_client.requests.request")
    def test_get_stock_success(self, mock_request, warehouse_client):
        warehouse_client._access_token = "valid-token"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"book_id": 1, "sku": "BOOK-001", "available_quantity": 10}
        ]
        mock_request.return_value = mock_response

        stock = warehouse_client.get_stock(book_id=1)

        assert stock is not None
        assert stock["book_id"] == 1
        assert stock["available_quantity"] == 10
        mock_request.assert_called_once()

    @patch("store.services.warehouse_client.requests.request")
    def test_get_stock_empty_returns_none(self, mock_request, warehouse_client):
        warehouse_client._access_token = "valid-token"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        stock = warehouse_client.get_stock(book_id=999)
        assert stock is None

    @patch("store.services.warehouse_client.requests.request")
    def test_reserve_stock_success(self, mock_request, warehouse_client):
        warehouse_client._access_token = "valid-token"
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 10, "status": "RESERVED"}
        mock_request.return_value = mock_response

        reservation = warehouse_client.reserve_stock(stock_item_id=1, order_id=42, quantity=2)

        assert reservation == {"id": 10, "status": "RESERVED"}
        mock_request.assert_called_once()


class TestWarehouseClientResilience:
    """Тести надійності: таймаути, помилки мережі та повторна авторизація."""

    @patch("store.services.warehouse_client.requests.request")
    def test_timeout_raises_custom_exception(self, mock_request, warehouse_client):
        warehouse_client._access_token = "valid-token"
        mock_request.side_effect = Timeout("Connection timed out")

        with pytest.raises(WarehouseServiceError, match="network timeout"):
            warehouse_client.get_stock(book_id=1)

    @patch("store.services.warehouse_client.requests.request")
    def test_network_failure_raises_custom_exception(self, mock_request, warehouse_client):
        warehouse_client._access_token = "valid-token"
        mock_request.side_effect = RequestException("DNS failure")

        with pytest.raises(WarehouseServiceError, match="Failed to communicate"):
            warehouse_client.get_stock(book_id=1)

    @patch("store.services.warehouse_client.requests.request")
    @patch.object(WarehouseClient, "_authenticate")
    def test_retry_on_401_expired_token(self, mock_auth, mock_request, warehouse_client):
        warehouse_client._access_token = "expired-token"

        # Перший виклик повертає 401, другий — успішний 200
        expired_response = Mock(status_code=401, text="Token expired")
        success_response = Mock(status_code=200)
        success_response.json.return_value = [{"book_id": 1, "available_quantity": 5}]

        mock_request.side_effect = [expired_response, success_response]

        stock = warehouse_client.get_stock(book_id=1)

        assert mock_auth.call_count == 1
        assert stock["available_quantity"] == 5
        assert mock_request.call_count == 2