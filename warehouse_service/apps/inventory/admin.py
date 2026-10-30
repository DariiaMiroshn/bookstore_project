from django.contrib import admin
from .models import Warehouse, StockItem, StockReservation


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    search_fields = ('name', 'code')


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ('sku', 'book_id', 'warehouse', 'quantity', 'reserved_quantity', 'available_qty_display')
    list_filter = ('warehouse',)
    search_fields = ('sku', 'book_id')

    # Відображення обчислюваного поля доступного залишку в списку адмінки
    @admin.display(description='Available')
    def available_qty_display(self, obj):
        return obj.available_quantity


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'stock_item', 'quantity', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_id', 'stock_item__sku')