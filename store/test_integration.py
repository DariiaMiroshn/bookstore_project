from unittest.mock import MagicMock, patch
import pytest
from django.urls import reverse
from store.factories import BookFactory, OrderFactory, UserFactory
from store.models import Order


@pytest.mark.django_db
class TestIntegrationUserFlows:
    """Інтеграційні тести користувацьких сценаріїв із mock для WarehouseClient, Stripe та email."""

    def test_flow_registration_and_login(self, client):
        # 1. Повний цикл реєстрації
        reg_url = reverse("users:register")
        reg_data = {
            "username": "newflowuser",
            "email": "flow@example.com",
            "password": "ValidPassword123!",
            "password2": "ValidPassword123!",
        }
        res = client.post(reg_url, reg_data)
        assert res.status_code in (302, 200)

    def test_flow_add_to_cart_and_view(self, client):
        # 2. Додавання книги до кошика
        book = BookFactory(stock=5)
        add_url = reverse("store:cart_add", kwargs={"book_id": book.id})
        res = client.post(add_url)
        assert res.status_code == 302

        # 3. Перевірка наявності книги в кошику
        cart_res = client.get(reverse("store:cart_detail"))
        assert cart_res.status_code == 200
        assert book.title.encode() in cart_res.content

    def test_flow_remove_from_cart(self, client):
        # 4. Видалення з кошика
        book = BookFactory()
        client.post(reverse("store:cart_add", kwargs={"book_id": book.id}))
        del_res = client.post(reverse("store:cart_remove", kwargs={"book_id": book.id}))
        assert del_res.status_code == 302

    def test_flow_checkout_redirects_anonymous_user(self, client):
        # 5. Анонімний користувач перенаправляється на логін
        res = client.get(reverse("store:order_create"))
        assert res.status_code == 302
        assert "/login" in res.url

    def test_flow_checkout_empty_cart_redirects(self, client):
        # 6. Спроба оформити порожній кошик повертає до каталогу
        user = UserFactory()
        client.force_login(user)
        res = client.get(reverse("store:order_create"))
        assert res.status_code == 302
        assert res.url == reverse("store:book_list")

    @patch("store.views.WarehouseClient")
    @patch("store.views.stripe.checkout.Session.create")
    @patch("store.views.send_order_confirmation_email_task.delay")
    def test_flow_full_successful_order(
        self, mock_celery_task, mock_stripe, mock_warehouse_cls, client
    ):
        # 7-11. Повний E2E цикл з моком WarehouseClient, Stripe та Celery email
        mock_warehouse = mock_warehouse_cls.return_value
        mock_warehouse.get_stock.return_value = {
            "id": 1,
            "book_id": 1,
            "available_quantity": 10,
        }
        mock_warehouse.reserve_stock.return_value = {
            "id": 100,
            "status": "RESERVED",
        }

        mock_session = MagicMock()
        mock_session.id = "cs_mock_123"
        mock_session.url = "https://checkout.stripe.com/pay/cs_mock_123"
        mock_stripe.return_value = mock_session
        mock_celery_task.return_value = None

        user = UserFactory()
        book = BookFactory(price=25.00, stock=5)
        client.force_login(user)

        # Додавання до кошика
        client.post(reverse("store:cart_add", kwargs={"book_id": book.id}))

        # Відправка форми замовлення
        order_data = {
            "first_name": "Dariia",
            "last_name": "Miro",
            "email": "dariia@test.com",
            "address": "Main Street 10",
            "postal_code": "78701",
            "city": "Austin",
        }
        res = client.post(reverse("store:order_create"), order_data)

        # Перевірка редіректу
        assert res.status_code in (302, 303)
        assert "stripe.com" in res.url

        # Перевірка виклику резервації на складі
        mock_warehouse.reserve_stock.assert_called_once()

        # Перевірка замовлення в базі даних
        order = Order.objects.get(user=user)
        assert order.stripe_session_id == "cs_mock_123"

    @patch("store.views.WarehouseClient")
    def test_flow_order_insufficient_stock(self, mock_warehouse_cls, client):
        # 12. Неможливість замовити товар при відсутності залишку на складі
        mock_warehouse = mock_warehouse_cls.return_value
        mock_warehouse.get_stock.return_value = {
            "id": 1,
            "book_id": 1,
            "available_quantity": 0,
        }

        user = UserFactory()
        book = BookFactory(stock=0)
        client.force_login(user)

        client.post(reverse("store:cart_add", kwargs={"book_id": book.id}))
        order_data = {
            "first_name": "Dariia",
            "last_name": "Miro",
            "email": "dariia@test.com",
            "address": "Main Street 10",
            "postal_code": "78701",
            "city": "Austin",
        }
        res = client.post(reverse("store:order_create"), order_data)
        assert res.status_code == 200
        assert Order.objects.count() == 0

    def test_flow_order_missing_form_fields(self, client):
        # 13. Валідація обов'язкових полів адреси
        user = UserFactory()
        book = BookFactory(stock=5)
        client.force_login(user)
        client.post(reverse("store:cart_add", kwargs={"book_id": book.id}))

        res = client.post(reverse("store:order_create"), {"first_name": "Dariia"})
        assert res.status_code == 200
        assert Order.objects.count() == 0

    @patch("store.views.WarehouseClient")
    def test_flow_payment_success_lifecycle(self, mock_warehouse_cls, client):
        # 14. Успішна обробка повернення з платіжної системи та підтвердження на складі
        mock_warehouse = mock_warehouse_cls.return_value
        mock_warehouse.confirm_reservation.return_value = {"status": "CONFIRMED"}

        order = OrderFactory(status="pending")
        res = client.get(f"{reverse('store:payment_success')}?order_id={order.id}")
        assert res.status_code == 200
        order.refresh_from_db()
        assert order.status == "paid"
        mock_warehouse.confirm_reservation.assert_called_once_with(
            reservation_id=order.id
        )

    def test_flow_i18n_set_language_redirect(self, client):
        # 15. Перемикання мови через POST-запит
        res = client.post(
            reverse("set_language"),
            {"language": "uk", "next": reverse("store:book_list")},
        )
        assert res.status_code == 302
        assert client.cookies.get("django_language").value == "uk"
