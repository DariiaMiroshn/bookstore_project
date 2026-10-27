# AI Code Review Report

Цей документ містить аналіз та результати Code Review трьох ключових 
контролерів (views)проєкту "Bookstore", проведеного за допомогою штучного інтелекту.

---

## 1. View: `order_create` (Оформлення замовлення та інтеграція Stripe)

### Оригінальний код:
```python
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
                    OrderItem.objects.create(order=order, book=book, price=item['price'], quantity=quantity)
                    line_items.append({
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {'name': book.title},
                            'unit_amount': int(item['price'] * 100),
                        },
                        'quantity': quantity,
                    })

                checkout_session = stripe.checkout.Session.create(
                    mode='payment',
                    line_items=line_items,
                    success_url=request.build_absolute_uri(reverse('store:payment_success') + f'?order_id={order.id}'),
                    cancel_url=request.build_absolute_uri(reverse('store:payment_cancel')),
                    client_reference_id=str(order.id)
                )
                order.stripe_session_id = checkout_session.id
                order.save()

            send_mail(
                subject=f"Order #{order.id} Confirmation",
                message=f"Hello {order.first_name},\n\nThank you for your order!",
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



"""Рекомендації AI:
1. Захист від race conditions під час списання залишків: 
Якщо двоє користувачів замовляють останню книгу одночасно, 
перевірка book.stock < quantity може пройти для обох. 
Рекомендовано використати select_for_update() у транзакції або блокування рядків.

2. Обробка винятків зовнішніх сервісів (Stripe та SMTP): 
Якщо Stripe або поштовий сервер повертають помилку мережі, 
транзакція має бути захищена, а користувач повинен отримати 
зрозуміле повідомлення замість стандартної помилки 500.

3. HTTP 303 See Other: Редірект на сторонній платіжний шлюз повинен 
явно використовувати статус 303 (це було враховано)."""

### Фінальний код::
```python

@login_required
def order_create(request):
    """Оформлення замовлення з атомарною транзакцією, перевіркою залишків та оплатою через Stripe."""
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
                    # Блокування рядка товару для запобігання гонитві станів
                    book = Book.objects.select_for_update().get(id=item['book'].id)
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
                            'product_data': {'name': book.title},
                            'unit_amount': int(item['price'] * 100),
                        },
                        'quantity': quantity,
                    })

                checkout_session = stripe.checkout.Session.create(
                    mode='payment',
                    line_items=line_items,
                    success_url=request.build_absolute_uri(reverse('store:payment_success') + f'?order_id={order.id}'),
                    cancel_url=request.build_absolute_uri(reverse('store:payment_cancel')),
                    client_reference_id=str(order.id)
                )

                order.stripe_session_id = checkout_session.id
                order.save()

            # Відправка email з безпечним перехопленням можливих помилок поштового сервера
            try:
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
            except Exception:
                pass  # Замовлення вже створено, помилка пошти не повинна ламати процес оплати

            cart.clear()
            return redirect(checkout_session.url, code=303)

        except ValueError as err:
            messages.error(request, str(err))
            return render(request, 'store/order_create.html', {'cart': cart})
        except stripe.error.StripeError:
            messages.error(request, "Payment gateway error. Please try again later.")
            return render(request, 'store/order_create.html', {'cart': cart})

    return render(request, 'store/order_create.html', {'cart': cart})



## 2. View: cart_add (Додавання книги до кошика)

### Оригінальний код:
```python

@require_POST
def cart_add(request, book_id):
    cart = Cart(request)
    book = get_object_or_404(Book, id=book_id)
    cart.add(book=book, quantity=1)
    return redirect('store:cart_detail')

"""Рекомендації AI:
1. Перевірка наявності товару (stock): 
Якщо кількість товару на складі дорівнює нулю (stock <= 0), 
користувач не повинен мати змоги додати його до кошика.

2. Зворотний зв'язок (Flash messages): Користувачу варто показати 
повідомлення про те, що товар успішно додано або що 
товару немає на складі.

3. Гнучкість кількості: Дозволити передавати кількість товару з 
форми (request.POST.get('quantity')), а не жорстко фіксувати 1."""


### Фінальний код::
```python

@require_POST
def cart_add(request, book_id):
    """Додавання книги до кошика з перевіркою наявності на складі."""
    cart = Cart(request)
    book = get_object_or_404(Book, id=book_id)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    if book.stock < quantity:
        messages.error(request, f"Cannot add '{book.title}'. Not enough stock available.")
        return redirect('store:book_detail', pk=book.id)

    cart.add(book=book, quantity=quantity)
    messages.success(request, f"'{book.title}' was successfully added to your cart.")
    return redirect('store:cart_detail')


## 3. View: async_book_list (Асинхронний список книг)

### Оригінальний код:
```python

async def async_book_list(request):
    """1. Async view для списку всіх книг"""
    books = [book async for book in Book.objects.all()]
    return await a_render(request, 'store/book_list.html', {'books': books})

"""Рекомендації AI:
1. Оптимізація запитів до бази (N+1 query problem): 
У списку книг зазвичай виводиться категорія. 
Використання .select_related('category') запобігає 
зайвим синхронним запитам до БД під час рендерингу.

2. Пагінація або ліміт: Завантаження абсолютно всіх записів 
через Book.objects.all() при зростанні бази перевантажить 
пам'ять контейнера. Варто додати базове обмеження або слайсинг."""

### Фінальний код:
async def async_book_list(request):
    """Асинхронне отримання каталогу книг з оптимізацією select_related."""
    books = [book async for book in Book.objects.select_related('category').all()[:50]]
    return await a_render(request, 'store/book_list.html', {'books': books})