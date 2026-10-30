from rest_framework.routers import DefaultRouter
from .views import WarehouseViewSet, StockItemViewSet, StockReservationViewSet

router = DefaultRouter()
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
router.register(r'items', StockItemViewSet, basename='stock-item')
router.register(r'reservations', StockReservationViewSet, basename='stock-reservation')

urlpatterns = router.urls