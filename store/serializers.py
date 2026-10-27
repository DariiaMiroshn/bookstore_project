from rest_framework import serializers
from .models import Category, Book, Order, OrderItem


# --- 1. Category Serializer ---

class CategorySerializer(serializers.ModelSerializer):
    # Серіалізатор для категорій книг.
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


# --- 2. Book Serializers ---

class BookSerializer(serializers.ModelSerializer):

    # Основний серіалізатор для книг.Включає вкладену категорію для читання (nested)та очікує category_id при створенні/редагуванні.

    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )

    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'author',
            'description',
            'price',
            'stock',
            'category',
            'category_id',
        ]


# --- 3. Order Item Serializer (Nested) ---

class OrderItemSerializer(serializers.ModelSerializer):

    # Вкладений серіалізатор для товарів у замовленні. Показує назву книги та вартість конкретної позиції.

    book_title = serializers.ReadOnlyField(source='book.title')
    total_cost = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'book', 'book_title', 'price', 'quantity', 'total_cost']
        read_only_fields = ['price']

    def get_total_cost(self, obj):
        return str(obj.get_cost())


# --- 4. Order Serializer (Nested) ---

class OrderSerializer(serializers.ModelSerializer):

    # Серіалізатор для замовлень із вкладеним списком позицій (OrderItem).

    items = OrderItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'first_name',
            'last_name',
            'email',
            'address',
            'postal_code',
            'city',
            'status',
            'created_at',
            'total_amount',
            'items',
        ]
        read_only_fields = ['id', 'user', 'status', 'created_at', 'total_amount', 'items']

    def get_total_amount(self, obj):
        return str(obj.get_total_cost())


# --- 5. Cart Serializers ---

class CartItemSerializer(serializers.Serializer):
    # Серіалізатор окремого елемента сесійного кошика.
    book_id = serializers.IntegerField()
    title = serializers.CharField(source='book.title', read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    quantity = serializers.IntegerField(min_value=1, default=1)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)


class CartSerializer(serializers.Serializer):
    # Серіалізатор усього кошика із загальною сумою.
    items = CartItemSerializer(many=True, read_only=True)
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_items = serializers.IntegerField(read_only=True)