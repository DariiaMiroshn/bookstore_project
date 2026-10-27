from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from store.api_views import (
    CategoryViewSet,
    BookViewSet,
    OrderViewSet,
    CartViewSet,
)

# Реєстрація DRF Routers для API
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='api-category')
router.register(r'books', BookViewSet, basename='api-book')
router.register(r'orders', OrderViewSet, basename='api-order')
router.register(r'cart', CartViewSet, basename='api-cart')

urlpatterns = [
    # 1. Головна панель адміністратора
    path('admin/', admin.site.urls),

    # 2. REST API Endpoints
    path('api/', include(router.urls)),

    # 3. JWT Authentication Endpoints (token obtain, refresh, verify)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # 4. API Документація Swagger (/api/docs/)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # 5. Маршрути веб-інтерфейсу магазину та користувачів
    path('users/', include('users.urls', namespace='users')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include('store.urls', namespace='store')),
]

# Налаштування для локальної розробки та debug_toolbar
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)