from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class Warehouse(models.Model):
    name = models.CharField(_('Warehouse Name'), max_length=120)
    code = models.CharField(_('Warehouse Code'), max_length=32, unique=True, db_index=True)
    address = models.CharField(_('Address'), max_length=255, blank=True)
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Warehouse')
        verbose_name_plural = _('Warehouses')

    def __str__(self):
        return f"{self.name} ({self.code})"


class StockItem(models.Model):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='stock_items',
        verbose_name=_('Warehouse')
    )
    book_id = models.PositiveBigIntegerField(
        _('ProjectA Book ID'),
        db_index=True,
        help_text=_('Reference ID of the book in ProjectA')
    )
    sku = models.CharField(_('SKU'), max_length=64, unique=True, db_index=True)
    quantity = models.PositiveIntegerField(_('Physical Quantity'), default=0)
    reserved_quantity = models.PositiveIntegerField(_('Reserved Quantity'), default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Stock Item')
        verbose_name_plural = _('Stock Items')
        constraints = [
            models.UniqueConstraint(
                fields=['warehouse', 'book_id'],
                name='unique_book_per_warehouse'
            )
        ]

    @property
    def available_quantity(self) -> int:
        return max(0, self.quantity - self.reserved_quantity)

    def clean(self):
        if self.reserved_quantity > self.quantity:
            raise ValidationError(
                _('Reserved quantity cannot exceed physical quantity.')
            )

    def __str__(self):
        return f"Book #{self.book_id} [{self.sku}] - Available: {self.available_quantity}"


class StockReservation(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        CONFIRMED = 'confirmed', _('Confirmed')
        CANCELLED = 'cancelled', _('Cancelled')

    order_id = models.PositiveBigIntegerField(_('ProjectA Order ID'), db_index=True)
    stock_item = models.ForeignKey(
        StockItem,
        on_delete=models.PROTECT,
        related_name='reservations',
        verbose_name=_('Stock Item')
    )
    quantity = models.PositiveIntegerField(_('Quantity'))
    status = models.CharField(
        _('Reservation Status'),
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Stock Reservation')
        verbose_name_plural = _('Stock Reservations')

    def __str__(self):
        return f"Order #{self.order_id} - SKU {self.stock_item.sku} ({self.quantity} pcs) [{self.status}]"