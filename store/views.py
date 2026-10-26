import stripe
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.mail import send_mail
from django.db import transaction
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from .cart import Cart
from .models import Book, Order, OrderItem, Category

stripe.api_key = settings.STRIPE_SECRET_KEY

# Безпечний рендеринг контексту (perms, user, session) в асинхронних views
a_render = sync_to_async(render)


# --- 1. Async views з асинхронними запитами до БД ---

async def async_book_list(request):
    """1. Async view для списку всіх книг"""
    books = [book async for book in Book.objects.all()]
    return await a_render(request, 'store/book_list.html', {'books': books})


async def async_book_detail(request, book_id):
    """2. Async view для детальної сторінки книги"""
    try:
        book = await Book.objects.aget(id=book_id)
    except Book.DoesNotExist:
        raise Http404("Book not found")
    return await a_render(request, 'store/book_detail.html', {'book': book})


async def async_category_books(request, category_slug):
    """3. Async view для фільтрації книг за категорією"""
    try:
        category = await Category.objects.aget(slug=category_slug)
    except Category.DoesNotExist:
        raise Http404("Category not found")

    books = [book async for book in Book.objects.filter(category=category)]
    return await a_render(request, 'store/book_list.html', {'books': books, 'category': category})


# --- 2. Стандартні CRUD views (Class-Based) ---

class BookListView(ListView):
    model = Book
    template_name = 'store/book_list.html'
    context_object_name = 'books'
    paginate_by = 4


class BookDetailView(DetailView):
    model = Book
    template_name = 'store/book_detail.html'
    context_object_name = 'book'


class BookCreateView(PermissionRequiredMixin, CreateView):
    model = Book
    template_name = 'store/book_form.html'
    fields = ['title', 'author', 'category', 'price', 'description', 'stock']
    success_url = reverse_lazy('store:book_list')
    permission_required = 'store.add_book'


class BookUpdateView(PermissionRequiredMixin, UpdateView):
    model = Book
    template_name = 'store/book_form.html'
    fields = ['title', 'author', 'category', 'price', 'description', 'stock']
    success_url = reverse_lazy('store:book_list')
    permission_required = 'store.change_book'


class BookDeleteView(PermissionRequiredMixin, DeleteView):
    model = Book
    template_name = 'store/book_confirm_delete.html'
    success_url = reverse_lazy('store:book_list')
    permission_required = 'store.delete_book'


# --- 3. Операції з кошиком (Cart) ---

@require_POST
def cart_add(request, book_id):
    cart = Cart(request)
    book = get_object_or_404(Book, id=book_id)
    cart.add(book=book, quantity=1)
    return redirect('store:cart_detail')


@require_POST
def cart_remove(request, book_id):
    cart = Cart(request)
    book = get_object_or_404(Book, id=book_id)
    cart.remove(book)
    return redirect('store:cart_detail')


def cart_detail(request):
    cart = Cart(request)
    return render(request, 'store/cart_detail.html', {'cart': cart})


# --- 4. Оформлення замовлення, Stripe та Email ---

@login_required
def order_create(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('store:book_list')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip() or request.user.first_name
        last_name = request.POST.get('last_name', '').strip() or request.user.last_name
        email = request.POST.get('email', '').strip() or request.user.email
        address = request.POST.get('address', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()
        city = request.POST.get('city', '').strip()

        if not all([first_name, last_name, email, address, postal_code, city]):
            messages.error(request, "Please fill in all required shipping and contact details.")
            return render(request, 'store/order_create.html', {'cart': cart})

        try:
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
                    book = item['book']
                    quantity = item['quantity']

                    if book.stock < quantity:
                        raise ValueError(f"Insufficient stock for book '{book.title}'. Available: {book.stock}.")

                    book.stock -= quantity
                    book.save()

                    OrderItem.objects.create(
                        order=order,
                        book=book,
                        price=item['price'],
                        quantity=quantity
                    )

                    line_items.append({
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': book.title,
                            },
                            'unit_amount': int(item['price'] * 100),
                        },
                        'quantity': quantity,
                    })

                success_url = request.build_absolute_uri(
                    reverse('store:payment_success') + f'?order_id={order.id}'
                )
                cancel_url = request.build_absolute_uri(reverse('store:payment_cancel'))

                checkout_session = stripe.checkout.Session.create(
                    mode='payment',
                    line_items=line_items,
                    success_url=success_url,
                    cancel_url=cancel_url,
                    client_reference_id=str(order.id)
                )

                order.stripe_session_id = checkout_session.id
                order.save()

            send_mail(
                subject=f"Order #{order.id} Confirmation",
                message=(
                    f"Hello {order.first_name},\n\n"
                    f"Thank you for your order! Your order #{order.id} has been created successfully.\n"
                    f"Total amount: ${order.get_total_cost()} USD.\n\n"
                    f"Best regards,\nBookstore Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.email],
                fail_silently=False,
            )

            cart.clear()
            return redirect(checkout_session.url, code=303)

        except ValueError as err:
            messages.error(request, str(err))
            return render(request, 'store/order_create.html', {'cart': cart})

    return render(request, 'store/order_create.html', {'cart': cart})


def payment_success(request):
    order_id = request.GET.get('order_id')
    if order_id:
        order = get_object_or_404(Order, id=order_id)
        order.status = 'paid'
        order.save()
    return render(request, 'store/payment_success.html', {'order_id': order_id})


def payment_cancel(request):
    return render(request, 'store/payment_cancel.html')