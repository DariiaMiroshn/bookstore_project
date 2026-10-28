from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Category name"))
    slug = models.SlugField(unique=True, verbose_name=_("URL-slug"))

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    author = models.CharField(max_length=100, verbose_name=_("Author"))
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Price")
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))
    stock = models.PositiveIntegerField(default=0, verbose_name=_("Stock quantity"))

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="books",
        verbose_name=_("Category"),
    )

    class Meta:
        verbose_name = _("Book")
        verbose_name_plural = _("Books")

    def __str__(self):
        return self.title


class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", _("Pending")),
        ("paid", _("Paid")),
        ("canceled", _("Canceled")),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name=_("User"),
    )
    first_name = models.CharField(max_length=50, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=50, verbose_name=_("Last Name"))
    email = models.EmailField(verbose_name=_("Email"))
    address = models.CharField(max_length=250, verbose_name=_("Address"))
    postal_code = models.CharField(max_length=20, verbose_name=_("Postal Code"))
    city = models.CharField(max_length=100, verbose_name=_("City"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name=_("Status"),
    )
    stripe_session_id = models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_("Stripe Session ID")
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self):
        return f"Order #{self.id} - {self.user}"

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, related_name="items", on_delete=models.CASCADE, verbose_name=_("Order")
    )
    book = models.ForeignKey(
        Book,
        related_name="order_items",
        on_delete=models.CASCADE,
        verbose_name=_("Book"),
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Price")
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Quantity"))

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")

    def __str__(self):
        return f"{self.book.title} (x{self.quantity})"

    def get_cost(self):
        return self.price * self.quantity
