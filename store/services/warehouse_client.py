import logging
from typing import Any, Dict, Optional
from django.conf import settings
import requests
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)


class WarehouseServiceError(Exception):
    """Custom base exception for Warehouse Service communication issues."""
    pass


class WarehouseClient:
    """
    HTTP Client responsible for communicating with Warehouse Microservice.
    Handles token authentication, timeouts, connection failures, and structured logging.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = (base_url or getattr(settings, 'WAREHOUSE_SERVICE_URL', 'http://127.0.0.1:8001')).rstrip('/')
        self.timeout = timeout or getattr(settings, 'WAREHOUSE_SERVICE_TIMEOUT', 3.0)
        self.username = getattr(settings, 'WAREHOUSE_SERVICE_USERNAME', '')
        self.password = getattr(settings, 'WAREHOUSE_SERVICE_PASSWORD', '')
        self._access_token: Optional[str] = None

    def _authenticate(self) -> None:
        """Obtains a fresh JWT access token from Warehouse Service."""
        url = f"{self.base_url}/api/v1/auth/token/"
        payload = {
            'username': self.username,
            'password': self.password,
        }
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            if response.status_code == 200:
                self._access_token = response.json().get('access')
                logger.info("Successfully authenticated with Warehouse Service.")
            else:
                logger.error(f"Failed to authenticate with Warehouse: {response.status_code} - {response.text}")
                raise WarehouseServiceError("Invalid Warehouse credentials.")
        except RequestException as exc:
            logger.error(f"Authentication request failed: {exc}")
            raise WarehouseServiceError("Cannot connect to Warehouse auth service.")

    def _get_headers(self) -> Dict[str, str]:
        if not self._access_token:
            self._authenticate()

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if self._access_token:
            headers['Authorization'] = f'Bearer {self._access_token}'
        return headers

    def _send_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_on_401: bool = True
    ) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Outgoing request to Warehouse: {method.upper()} {url} | Params: {params} | Data: {data}")

        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            logger.info(f"Warehouse response received: {response.status_code} from {url}")

            # Якщо токен протух (401), оновлюємо його один раз і повторюємо запит
            if response.status_code == 401 and retry_on_401:
                logger.warning("Token expired. Refreshing token and retrying request...")
                self._authenticate()
                return self._send_request(method, endpoint, data, params, retry_on_401=False)

            if response.status_code in (200, 201):
                return response.json()

            logger.warning(f"Warehouse returned non-success status: {response.status_code} - Body: {response.text}")
            return None

        except Timeout:
            logger.error(f"Timeout occurred while connecting to Warehouse service at {url} (limit: {self.timeout}s)")
            raise WarehouseServiceError("Warehouse service is currently unreachable due to network timeout.")

        except RequestException as exc:
            logger.error(f"Network error during Warehouse communication at {url}: {exc}")
            raise WarehouseServiceError("Failed to communicate with Warehouse service.")

    def get_stock(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Fetches stock availability details for a given book_id from warehouse inventory."""
        endpoint = "/api/v1/inventory/items/"
        result = self._send_request(method='get', endpoint=endpoint, params={'book_id': book_id})
        if result and isinstance(result, list) and len(result) > 0:
            return result[0]
        return None

    def reserve_stock(self, stock_item_id: int, order_id: int, quantity: int) -> Optional[Dict[str, Any]]:
        """Creates a stock reservation for a specific order."""
        endpoint = f"/api/v1/inventory/items/{stock_item_id}/reserve/"
        payload = {'order_id': order_id, 'quantity': quantity}
        return self._send_request(method='post', endpoint=endpoint, data=payload)

    def confirm_reservation(self, reservation_id: int) -> Optional[Dict[str, Any]]:
        """Confirms order completion and marks stock deduction."""
        endpoint = f"/api/v1/inventory/reservations/{reservation_id}/confirm/"
        return self._send_request(method='post', endpoint=endpoint)

    def cancel_reservation(self, reservation_id: int) -> Optional[Dict[str, Any]]:
        """Cancels reservation and restores available stock."""
        endpoint = f"/api/v1/inventory/reservations/{reservation_id}/cancel/"
        return self._send_request(method='post', endpoint=endpoint)