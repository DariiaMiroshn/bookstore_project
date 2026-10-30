import stripe
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.cache import cache
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from store.services.warehouse_client import WarehouseClient, WarehouseServiceError
from .cart import Cart
from .models import Book, Category, Order, OrderItem
from .tasks import send_order_confirmation_email_task

stripe.api_key = settings.STRIPE_SECRET_KEY

# Безпечний рендеринг контексту (perms, user, session) в асинхронних views
a_render = sync_to_async(render)


# --- 1. Async views з асинхронними запитами до БД ---


async def async_book_list(request):
    """
    Асинхронне відображення списку всіх книг.
    Використовує асинхронний генератор списку для неблокуючого читання з БД.
    """
    books = [book async for book in Book.objects.all()]
    return await a_render(request, "store/book_list.html", {"books": books})


async def async_book_detail(request, book_id):
    """
    Асинхронне відображення детальної інформації про книгу.
    Отримує об'єкт через aget() або генерує виняток Http404.
    """
    try:
        book = await Book.objects.aget(id=book_id)
    except Book.DoesNotExist:
        raise Http404("Book not found")
    return await a_render(request, "store/book_detail.html", {"book": book})


async def async_category_books(request, category_slug):
    """
    Асинхронне відображення списку книг, відфільтрованих за категорією.
    Отримує категорію за slug через aget() та повертає відповідні книги.
    """
    try:
        category = await Category.objects.aget(slug=category_slug)
    except Category.DoesNotExist:
        raise Http404("Category not found")

    books = [book async for book in Book.objects.filter(category=category)]
    return await a_render(
        request, "store/book_list.html", {"books": books, "category": category}
    )


# --- 2. Стандартні CRUD views (Class-Based) з Redis Low-level кешуванням ---


class BookListView(ListView):
    """Публічний каталог книг із пагінацією по 4 записи на сторінку."""

    model = Book
    template_name = "store/book_list.html"
    context_object_name = "books"
    paginate_by = 4


class BookDetailView(DetailView):
    """
    Детальна сторінка книги з Low-level Redis кешуванням на 15 хвилин.
    """

    model = Book
    template_name = "store/book_detail.html"
    context_object_name = "book"

    def get_object(self, queryset=None):
        book_id = self.kwargs.get(self.pk_url_kwarg or "pk")
        cache_key = f"book_detail_{book_id}"
        cached_book = cache.get(cache_key)

        if cached_book is not None:
            return cached_book

        book = super().get_object(queryset)
        cache.set(cache_key, book, timeout=60 * 15)
        return book


class BookCreateView(PermissionRequiredMixin, CreateView):
    """Форма додавання нової книги (доступ лише з дозволом store.add_book)."""

    model = Book
    template_name = "store/book_form.html"
    fields = ["title", "author", "category", "price", "description", "stock"]
    success_url = reverse_lazy("store:book_list")
    permission_required = "store.add_book"


class BookUpdateView(PermissionRequiredMixin, UpdateView):
    """Форма редагування книги (доступ лише з дозволом store.change_book)."""

    model = Book
    template_name = "store/book_form.html"
    fields = ["title", "author", "category", "price", "description", "stock"]
    success_url = reverse_lazy("store:book_list")
    permission_required = "store.change_book"


class BookDeleteView(PermissionRequiredMixin, DeleteView):
    """Сторінка видалення книги (доступ лише з дозволом store.delete_book)."""

    model = Book
    template_name = "store/book_confirm_delete.html"
    success_url = reverse_lazy("store:book_list")
    permission_required = "store.delete_book"


# --- 3. Операції з кошиком (Cart) ---


@require_POST
def cart_add(request, book_id):
    """Додавання книги до сесійного кошика покупця."""
    cart = Cart(request)
    book = get_object_or_404(Book, id=book_id)
    cart.add(book=book, quantity=1)
    return redirect("store:cart_detail")


@require_POST
def cart_remove(request, book_id):
    """Видалення вказаної книги із сесійного кошика."""
    cart = Cart(request)
    book = get_object_or_404(Book, id=book_id)
    cart.remove(book)
    return redirect("store:cart_detail")


def cart_detail(request):
    """Відображення сторінки з поточним вмістом кошика."""
    cart = Cart(request)
    return render(request, "store/cart_detail.html", {"cart": cart})


# --- 4. Оформлення замовлення, Stripe та асинхронний Celery Email ---


@login_required
def order_create(request):
    """
    Оформлення замовлення:
    валідація полів адреси, перевірка та резервування на віддаленому складі (Warehouse Service),
    створення Stripe сесії та відправка email у фоновій задачі Celery.
    """
    cart = Cart(request)
    if len(cart) == 0:
        return redirect("store:book_list")

    if request.method == "POST":
        first_name = (
            request.POST.get("first_name", "").strip() or request.user.first_name
        )
        last_name = request.POST.get("last_name", "").strip() or request.user.last_name
        email = request.POST.get("email", "").strip() or request.user.email
        address = request.POST.get("address", "").strip()
        postal_code = request.POST.get("postal_code", "").strip()
        city = request.POST.get("city", "").strip()

        if not all([first_name, last_name, email, address, postal_code, city]):
            messages.error(
                request, "Please fill in all required shipping and contact details."
            )
            return render(request, "store/order_create.html", {"cart": cart})

        warehouse_client = WarehouseClient()

        try:
            # 1. Мікросервісна валідація наявності товарів на складі
            for item in cart:
                book = item["book"]
                quantity = item["quantity"]

                stock_data = warehouse_client.get_stock(book_id=book.id)
                if not stock_data:
                    raise ValueError(
                        f"Товар '{book.title}' наразі відсутній на складі."
                    )

                available = stock_data.get("available_quantity", 0)
                if available < quantity:
                    raise ValueError(
                        f"Недостатньо залишку для книги '{book.title}'. Доступно: {available}, замовлено: {quantity}."
                    )

            # 2. Створення замовлення та резервації на складі
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    address=address,
                    postal_code=postal_code,
                    city=city,
                )

                line_items = []
                for item in cart:
                    book = item["book"]
                    quantity = item["quantity"]

                    stock_data = warehouse_client.get_stock(book_id=book.id)
                    stock_item_id = stock_data["id"]

                    # Створюємо резервацію на складі
                    reservation = warehouse_client.reserve_stock(
                        stock_item_id=stock_item_id,
                        order_id=order.id,
                        quantity=quantity,
                    )
                    if not reservation:
                        raise ValueError(
                            f"Не вдалося зарезервувати залишок для '{book.title}'."
                        )

                    OrderItem.objects.create(
                        order=order, book=book, price=item["price"], quantity=quantity
                    )

                    line_items.append(
                        {
                            "price_data": {
                                "currency": "usd",
                                "product_data": {
                                    "name": book.title,
                                },
                                "unit_amount": int(item["price"] * 100),
                            },
                            "quantity": quantity,
                        }
                    )

                # Формування зовнішньої адреси редіректу на порт Nginx 8080
                base_url = request.build_absolute_uri("/").rstrip("/")
                if ("localhost" in base_url or "127.0.0.1" in base_url) and ":8080" not in base_url:
                    base_url = "http://127.0.0.1:8080"

                success_url = f"{base_url}{reverse('store:payment_success')}?order_id={order.id}"
                cancel_url = f"{base_url}{reverse('store:payment_cancel')}"

                checkout_session = stripe.checkout.Session.create(
                    mode="payment",
                    line_items=line_items,
                    success_url=success_url,
                    cancel_url=cancel_url,
                    client_reference_id=str(order.id),
                )

                order.stripe_session_id = checkout_session.id
                order.save()

            # Фонова відправка email через Celery
            send_order_confirmation_email_task.delay(order.id)

            cart.clear()
            return redirect(checkout_session.url, code=303)

        except stripe.error.StripeError as err:
            messages.error(request, f"Помилка платіжної системи Stripe: {err}")
            return render(request, "store/order_create.html", {"cart": cart})

        except WarehouseServiceError as err:
            messages.error(request, f"Сервіс складу тимчасово недоступний: {err}")
            return render(request, "store/order_create.html", {"cart": cart})

        except ValueError as err:
            messages.error(request, str(err))
            return render(request, "store/order_create.html", {"cart": cart})

    return render(request, "store/order_create.html", {"cart": cart})


def payment_success(request):
    """Обробка успішної оплати через Stripe та підтвердження резервації на складі."""
    order_id = request.GET.get("order_id")
    if order_id:
        order = get_object_or_404(Order, id=order_id)
        if order.status != "paid":
            order.status = "paid"
            order.save()

            # Підтвердження резервацій на складі
            try:
                warehouse_client = WarehouseClient()
                warehouse_client.confirm_reservation(reservation_id=order.id)
            except Exception as exc:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Не вдалося підтвердити резервацію на складі для order {order_id}: {exc}"
                )

    return render(request, "store/payment_success.html", {"order_id": order_id})


def payment_cancel(request):
    """Обробка скасування оплати: зняття броні зі складу та зміна статусу."""
    order_id = request.GET.get("order_id")
    if order_id:
        order = get_object_or_404(Order, id=order_id)
        if order.status != "cancelled":
            order.status = "cancelled"
            order.save()

            # Скасовуємо резервацію на складі, щоб повернути залишок у вільний продаж
            warehouse_client = WarehouseClient()
            try:
                warehouse_client.cancel_reservation(reservation_id=order.id)
            except WarehouseServiceError as exc:
                messages.warning(
                    request, f"Помилка скасування резерву на складі: {exc}"
                )

    return render(request, "store/payment_cancel.html")


def health_check(request):
    """
    Health check endpoint для систем моніторингу та хмарного деплою.
    Повертає статус 200 OK і стан основних компонентів.
    """
    return JsonResponse({"status": "healthy", "service": "bookstore_api"}, status=200)
