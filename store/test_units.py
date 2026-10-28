from unittest.mock import patch
import pytest
from django.urls import reverse
from store.models import Category, Book, Order, OrderItem
from store.factories import (
    UserFactory,
    CategoryFactory,
    BookFactory,
    OrderFactory,
    OrderItemFactory,
)


@pytest.mark.django_db
class TestUnitModels:
    """Unit-тести моделей (1-8)"""

    def test_category_str(self):
        category = CategoryFactory(name="Sci-Fi")
        assert str(category) == "Sci-Fi"

    def test_book_str(self):
        book = BookFactory(title="Dune")
        assert str(book) == "Dune"

    def test_order_str(self):
        order = OrderFactory(id=10)
        assert "Order #10" in str(order)

    def test_order_item_str(self):
        book = BookFactory(title="1984")
        item = OrderItemFactory(book=book, quantity=2)
        assert str(item) == "1984 (x2)"

    def test_order_item_get_cost(self):
        item = OrderItemFactory(price=15.00, quantity=3)
        assert item.get_cost() == 45.00

    def test_order_get_total_cost(self):
        order = OrderFactory()
        OrderItemFactory(order=order, price=10.00, quantity=2)
        OrderItemFactory(order=order, price=5.00, quantity=1)
        assert order.get_total_cost() == 25.00

    def test_book_default_stock(self):
        book = Book.objects.create(
            title="Clean Code",
            author="Uncle Bob",
            price=30.00,
            category=CategoryFactory(),
        )
        assert book.stock == 0

    def test_order_default_status(self):
        order = OrderFactory()
        assert order.status == "pending"


@pytest.mark.django_db
class TestUnitValidationAndCart:
    """Unit-тести логіки кошика та валідації (9-12)"""

    def test_order_item_cost_zero_quantity(self):
        item = OrderItemFactory(price=20.00, quantity=0)
        assert item.get_cost() == 0

    def test_category_slug_unique(self):
        cat = CategoryFactory(slug="unique-cat")
        assert cat.slug == "unique-cat"

    def test_book_price_precision(self):
        book = BookFactory(price=19.99)
        assert float(book.price) == 19.99

    def test_order_address_fields(self):
        order = OrderFactory(address="742 Evergreen Terrace", city="Springfield")
        assert order.address == "742 Evergreen Terrace"
        assert order.city == "Springfield"


@pytest.mark.django_db
class TestUnitViews:
    """Unit-тести стандартних та async views (13-24)"""

    def test_book_list_view_status(self, client):
        response = client.get(reverse("store:book_list"))
        assert response.status_code == 200

    def test_book_detail_view_status(self, client):
        book = BookFactory()
        response = client.get(reverse("store:book_detail", kwargs={"pk": book.pk}))
        assert response.status_code == 200

    def test_book_detail_404(self, client):
        response = client.get(reverse("store:book_detail", kwargs={"pk": 9999}))
        assert response.status_code == 404

    def test_cart_detail_view_status(self, client):
        response = client.get(reverse("store:cart_detail"))
        assert response.status_code == 200

    def test_payment_cancel_view_status(self, client):
        response = client.get(reverse("store:payment_cancel"))
        assert response.status_code == 200

    def test_payment_success_without_order(self, client):
        response = client.get(reverse("store:payment_success"))
        assert response.status_code == 200

    def test_payment_success_marks_order_paid(self, client):
        order = OrderFactory(status="pending")
        response = client.get(f"{reverse('store:payment_success')}?order_id={order.id}")
        assert response.status_code == 200
        order.refresh_from_db()
        assert order.status == "paid"

    def test_async_book_list_status(self, client):
        BookFactory.create_batch(2)
        response = client.get(reverse("store:async_book_list"))
        assert response.status_code == 200

    def test_async_book_detail_status(self, client):
        book = BookFactory()
        response = client.get(
            reverse("store:async_book_detail", kwargs={"book_id": book.id})
        )
        assert response.status_code == 200

    def test_async_book_detail_404(self, client):
        response = client.get(
            reverse("store:async_book_detail", kwargs={"book_id": 9999})
        )
        assert response.status_code == 404

    def test_async_category_books_status(self, client):
        cat = CategoryFactory(slug="science")
        BookFactory(category=cat)
        response = client.get(
            reverse("store:async_category_books", kwargs={"category_slug": "science"})
        )
        assert response.status_code == 200

    def test_async_category_books_404(self, client):
        response = client.get(
            reverse(
                "store:async_category_books", kwargs={"category_slug": "missing-slug"}
            )
        )
        assert response.status_code == 404
