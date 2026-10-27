from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Category, Book, Order
from .cart import Cart
from .serializers import (
    CategorySerializer,
    BookSerializer,
    OrderSerializer,
    CartSerializer,
)
from .permissions import IsOwnerOrReadOnly


# --- 1. Category ViewSet ---

class CategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD для категорій книг.
    Читання доступне всім, додавання/зміна — лише адміністраторам.
    """
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    filter_backends = [SearchFilter]
    search_fields = ['name', 'slug']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


# --- 2. Book ViewSet ---

class BookViewSet(viewsets.ModelViewSet):
    """
    CRUD для книг із підтримкою фільтрації, пошуку та сортування.
    Читання доступне всім, створення/зміна/видалення — лише адміністраторам.
    """
    queryset = Book.objects.select_related('category').all().order_by('-id')
    serializer_class = BookSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'category__slug']
    search_fields = ['title', 'author', 'description']
    ordering_fields = ['price', 'title', 'stock']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


# --- 3. Order ViewSet ---

class OrderViewSet(viewsets.ModelViewSet):
    """
    Управління замовленнями.
    Користувач бачить лише власні замовлення (або всі, якщо адміністратор).
    Редагування/видалення захищено кастомним дозволом IsOwnerOrReadOnly.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.prefetch_related('items__book').all().order_by('-created_at')
        return Order.objects.filter(user=user).prefetch_related('items__book').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# --- 4. Cart ViewSet ---

class CartViewSet(viewsets.ViewSet):
    """
    Управління кошиком через API (сесійне сховище).
    Доступно будь-якому користувачеві (гостю або авторизованому).
    """
    permission_classes = [permissions.AllowAny]

    def list(self, request):
        """Отримання вмісту кошика."""
        cart = Cart(request)
        cart_items = [
            {
                'book_id': item['book'].id,
                'book': item['book'],
                'price': item['price'],
                'quantity': item['quantity'],
                'total_price': item['total_price'],
            }
            for item in cart
        ]
        data = {
            'items': cart_items,
            'total_cost': cart.get_total_price(),
            'total_items': len(cart),
        }
        serializer = CartSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add(self, request):
        """Додавання книги до кошика або зміна її кількості."""
        book_id = request.data.get('book_id')
        quantity = int(request.data.get('quantity', 1))

        if not book_id:
            return Response({'error': 'book_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

        if book.stock < quantity:
            return Response(
                {'error': f'Not enough stock. Available: {book.stock}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart = Cart(request)
        cart.add(book=book, quantity=quantity)
        return Response({'message': f"'{book.title}' added to cart", 'total_items': len(cart)})

    @action(detail=False, methods=['post'])
    def remove(self, request):
        """Видалення товару з кошика."""
        book_id = request.data.get('book_id')
        if not book_id:
            return Response({'error': 'book_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

        cart = Cart(request)
        cart.remove(book)
        return Response({'message': f"'{book.title}' removed from cart", 'total_items': len(cart)})

    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Повне очищення кошика."""
        cart = Cart(request)
        cart.clear()
        return Response({'message': 'Cart cleared'})