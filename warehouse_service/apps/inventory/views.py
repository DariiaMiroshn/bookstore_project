from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Warehouse, StockItem, StockReservation
from .serializers import (
    WarehouseSerializer,
    StockItemSerializer,
    ReserveStockSerializer,
    StockReservationSerializer,
)


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    filterset_fields = ("is_active", "code")
    search_fields = ("name", "code")


class StockItemViewSet(viewsets.ModelViewSet):
    queryset = StockItem.objects.select_related("warehouse").all()
    serializer_class = StockItemSerializer
    search_fields = ("sku",)

    def get_queryset(self):
        # Фільтрація за book_id для швидкого пошуку залишків конкретної книги з ProjectA
        queryset = super().get_queryset()
        book_id = self.request.query_params.get("book_id")
        if book_id is not None:
            queryset = queryset.filter(book_id=book_id)
        return queryset

    @extend_schema(
        request=ReserveStockSerializer, responses={201: StockReservationSerializer}
    )
    @action(detail=True, methods=["post"], url_path="reserve")
    @transaction.atomic
    def reserve(self, request, pk=None):
        """
        Атомарне резервування товару під замовлення з ProjectA.
        Використовує select_for_update() для уникнення race conditions.
        """
        stock_item = StockItem.objects.select_for_update().filter(pk=pk).first()
        if not stock_item:
            return Response(
                {"detail": "Stock item not found."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ReserveStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.validated_data["quantity"]
        order_id = serializer.validated_data["order_id"]

        if stock_item.available_quantity < quantity:
            return Response(
                {
                    "detail": "Insufficient stock available.",
                    "available_quantity": stock_item.available_quantity,
                    "requested_quantity": quantity,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Збільшуємо кількість у резерві
        stock_item.reserved_quantity += quantity
        stock_item.save(update_fields=["reserved_quantity", "updated_at"])

        reservation = StockReservation.objects.create(
            order_id=order_id,
            stock_item=stock_item,
            quantity=quantity,
            status=StockReservation.Status.PENDING,
        )

        output_serializer = StockReservationSerializer(reservation)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class StockReservationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockReservation.objects.select_related(
        "stock_item", "stock_item__warehouse"
    ).all()
    serializer_class = StockReservationSerializer
    filterset_fields = ("order_id", "status")

    @extend_schema(responses={200: StockReservationSerializer})
    @action(detail=True, methods=["post"], url_path="confirm")
    @transaction.atomic
    def confirm(self, request, pk=None):
        """
        Підтвердження продажу: фактичне списання залишку та закриття резерву.
        """
        reservation = StockReservation.objects.select_for_update().filter(pk=pk).first()
        if not reservation:
            return Response(
                {"detail": "Reservation not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if reservation.status != StockReservation.Status.PENDING:
            return Response(
                {
                    "detail": f"Cannot confirm reservation with status {reservation.status}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        stock_item = StockItem.objects.select_for_update().get(
            pk=reservation.stock_item_id
        )

        # Списуємо фізичний залишок і знімаємо з резерву
        stock_item.quantity -= reservation.quantity
        stock_item.reserved_quantity -= reservation.quantity
        stock_item.save(update_fields=["quantity", "reserved_quantity", "updated_at"])

        reservation.status = StockReservation.Status.CONFIRMED
        reservation.save(update_fields=["status", "updated_at"])

        return Response(
            self.get_serializer(reservation).data, status=status.HTTP_200_OK
        )

    @extend_schema(responses={200: StockReservationSerializer})
    @action(detail=True, methods=["post"], url_path="cancel")
    @transaction.atomic
    def cancel(self, request, pk=None):
        """
        Скасування резерву: повернення зарезервованої кількості в доступні залишки.
        """
        reservation = StockReservation.objects.select_for_update().filter(pk=pk).first()
        if not reservation:
            return Response(
                {"detail": "Reservation not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if reservation.status != StockReservation.Status.PENDING:
            return Response(
                {
                    "detail": f"Cannot cancel reservation with status {reservation.status}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        stock_item = StockItem.objects.select_for_update().get(
            pk=reservation.stock_item_id
        )
        stock_item.reserved_quantity -= reservation.quantity
        stock_item.save(update_fields=["reserved_quantity", "updated_at"])

        reservation.status = StockReservation.Status.CANCELLED
        reservation.save(update_fields=["status", "updated_at"])

        return Response(
            self.get_serializer(reservation).data, status=status.HTTP_200_OK
        )
