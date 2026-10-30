import pytest
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.inventory.models import Warehouse, StockItem, StockReservation


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_user():
    return User.objects.create_user(username='test_service_user', password='securepassword123')


@pytest.fixture
def authenticated_client(api_client, auth_user):
    api_client.force_authenticate(user=auth_user)
    return api_client


@pytest.fixture
def warehouse():
    return Warehouse.objects.create(name='Test Warehouse', code='WH-TEST-01')


@pytest.fixture
def stock_item(warehouse):
    return StockItem.objects.create(
        warehouse=warehouse,
        book_id=101,
        sku='TEST-SKU-101',
        quantity=10,
        reserved_quantity=0,
    )


@pytest.mark.django_db
class TestInventoryAPI:

    def test_get_stock_items_by_book_id(self, authenticated_client, stock_item):
        response = authenticated_client.get(f'/api/v1/inventory/items/?book_id={stock_item.book_id}')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]['sku'] == stock_item.sku
        assert data[0]['available_quantity'] == 10

    def test_reserve_stock_success(self, authenticated_client, stock_item):
        payload = {'order_id': 5001, 'quantity': 3}
        response = authenticated_client.post(f'/api/v1/inventory/items/{stock_item.id}/reserve/', payload)

        assert response.status_code == status.HTTP_201_CREATED
        stock_item.refresh_from_db()
        assert stock_item.reserved_quantity == 3
        assert stock_item.available_quantity == 7

        reservation = StockReservation.objects.get(order_id=5001)
        assert reservation.status == StockReservation.Status.PENDING
        assert reservation.quantity == 3

    def test_reserve_stock_insufficient(self, authenticated_client, stock_item):
        payload = {'order_id': 5002, 'quantity': 15}
        response = authenticated_client.post(f'/api/v1/inventory/items/{stock_item.id}/reserve/', payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        stock_item.refresh_from_db()
        assert stock_item.reserved_quantity == 0

    def test_confirm_reservation(self, authenticated_client, stock_item):
        # Попереднє резервування
        reservation = StockReservation.objects.create(
            order_id=5003,
            stock_item=stock_item,
            quantity=4,
            status=StockReservation.Status.PENDING
        )
        stock_item.reserved_quantity = 4
        stock_item.save()

        # Підтвердження
        response = authenticated_client.post(f'/api/v1/inventory/reservations/{reservation.id}/confirm/')
        assert response.status_code == status.HTTP_200_OK

        stock_item.refresh_from_db()
        reservation.refresh_from_db()
        assert stock_item.quantity == 6
        assert stock_item.reserved_quantity == 0
        assert reservation.status == StockReservation.Status.CONFIRMED

    def test_cancel_reservation(self, authenticated_client, stock_item):
        reservation = StockReservation.objects.create(
            order_id=5004,
            stock_item=stock_item,
            quantity=2,
            status=StockReservation.Status.PENDING
        )
        stock_item.reserved_quantity = 2
        stock_item.save()

        response = authenticated_client.post(f'/api/v1/inventory/reservations/{reservation.id}/cancel/')
        assert response.status_code == status.HTTP_200_OK

        stock_item.refresh_from_db()
        reservation.refresh_from_db()
        assert stock_item.reserved_quantity == 0
        assert stock_item.quantity == 10
        assert reservation.status == StockReservation.Status.CANCELLED