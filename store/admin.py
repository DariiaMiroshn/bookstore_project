from django.contrib import admin
from .models import Category, Book, Order, OrderItem


class BookInline(admin.TabularInline):
    model = Book
    extra = 1  # Кількість порожніх рядків для додавання нових книг
    fields = ('title', 'author', 'price', 'stock')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}  # Автоматична генерація slug з name
    inlines = [BookInline]  # Вбудовані книги на сторінці категорії


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'price', 'stock')
    list_filter = ('category',)  # Фільтрація за категорією у правому меню
    search_fields = ('title', 'author')  # Пошук за назвою та автором
    list_editable = ('price', 'stock')  # Швидке редагування ціни та залишків зі списку


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['book']
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'first_name', 'last_name', 'email', 'status', 'created_at', 'get_total_cost']
    list_filter = ['status', 'created_at']
    inlines = [OrderItemInline]