import pytest
from decimal import Decimal
from store.models import Book, Order, OrderItem
from store.factories import CategoryFactory, BookFactory, OrderFactory, OrderItemFactory


@pytest.mark.django_db
class TestAIGeneratedBookModel:
    """Тести моделі Book, згенеровані за допомогою AI."""

    def test_book_creation_and_str(self):
        # Generated with AI, reviewed and modified
        book = BookFactory(title="Python Testing with AI", price=29.99)
        assert str(book) == "Python Testing with AI"
        assert book.price == 29.99

    def test_book_stock_decreases_correctly(self):
        # Generated with AI, reviewed and modified
        book = BookFactory(stock=10)
        book.stock -= 3
        book.save()
        book.refresh_from_db()
        assert book.stock == 7

    def test_book_category_relation(self):
        # Generated with AI, reviewed and modified
        category = CategoryFactory(name="Programming", slug="programming")
        book = BookFactory(title="Django Pro", category=category)
        assert book.category.name == "Programming"
        assert book.category.slug == "programming"


@pytest.mark.django_db
class TestAIGeneratedOrderModel:
    """Тести моделі Order, згенеровані за допомогою AI."""

    def test_order_creation_and_str(self):
        # Generated with AI, reviewed and modified
        order = OrderFactory(first_name="Dariia", last_name="Miro")
        assert f"Order #{order.id}" in str(order)
        assert order.status == "pending"

    def test_order_status_update_to_paid(self):
        # Generated with AI, reviewed and modified
        order = OrderFactory(status="pending")
        order.status = "paid"
        order.save()
        order.refresh_from_db()
        assert order.status == "paid"

    def test_order_total_cost_calculation(self):
        # Generated with AI, reviewed and modified
        order = OrderFactory()
        OrderItemFactory(order=order, price=Decimal("12.50"), quantity=2)
        OrderItemFactory(order=order, price=Decimal("20.00"), quantity=1)
        # 12.50 * 2 + 20.00 * 1 = 45.00
        assert order.get_total_cost() == Decimal("45.00")


@pytest.mark.django_db
class TestAIGeneratedOrderItemModel:
    """Тести моделі OrderItem, згенеровані за допомогою AI."""

    def test_order_item_cost_calculation(self):
        # Generated with AI, reviewed and modified
        item = OrderItemFactory(price=Decimal("15.00"), quantity=3)
        assert item.get_cost() == Decimal("45.00")

    def test_order_item_str_representation(self):
        # Generated with AI, reviewed and modified
        book = BookFactory(title="Fluent Python")
        item = OrderItemFactory(book=book, quantity=4)
        assert str(item) == "Fluent Python (x4)"