from rest_framework import serializers
from .models import Warehouse, StockItem, StockReservation


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ("id", "name", "code", "address", "is_active", "created_at")
        read_only_fields = ("id", "created_at")


class StockItemSerializer(serializers.ModelSerializer):
    available_quantity = serializers.IntegerField(read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)

    class Meta:
        model = StockItem
        fields = (
            "id",
            "warehouse",
            "warehouse_code",
            "book_id",
            "sku",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "reserved_quantity",
            "available_quantity",
            "updated_at",
        )


class ReserveStockSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class StockReservationSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="stock_item.sku", read_only=True)
    book_id = serializers.IntegerField(source="stock_item.book_id", read_only=True)

    class Meta:
        model = StockReservation
        fields = (
            "id",
            "order_id",
            "stock_item",
            "book_id",
            "sku",
            "quantity",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "status", "created_at", "updated_at")
