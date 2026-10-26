from django.db import models
from django.conf import settings
from decimal import Decimal

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Category name")
    slug = models.SlugField(unique=True, verbose_name="URL-slug")

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200, verbose_name="Title")
    author = models.CharField(max_length=100, verbose_name="Author")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price")
    description = models.TextField(blank=True, verbose_name="Description")
    stock = models.PositiveIntegerField(default=0, verbose_name="Stock quantity")

    # Зв'язок "один-до-багатьох": у однієї категорії може бути багато книг
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='books',
        verbose_name="Category"
    )

    class Meta:
        verbose_name = "Book"
        verbose_name_plural = "Books"

    def __str__(self):
        return self.title


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('canceled', 'Canceled'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name="User"
    )
    first_name = models.CharField(max_length=50, verbose_name="First Name")
    last_name = models.CharField(max_length=50, verbose_name="Last Name")
    email = models.EmailField(verbose_name="Email")
    address = models.CharField(max_length=250, verbose_name="Address")
    postal_code = models.CharField(max_length=20, verbose_name="Postal Code")
    city = models.CharField(max_length=100, verbose_name="City")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="Stripe Session ID")

    class Meta:
        ordering = ('-created_at',)
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return f"Order #{self.id} - {self.user}"

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name="Order"
    )
    book = models.ForeignKey(
        Book,
        related_name='order_items',
        on_delete=models.CASCADE,
        verbose_name="Book"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")

    def __str__(self):
        return f"{self.book.title} (x{self.quantity})"

    def get_cost(self):
        return self.price * self.quantity