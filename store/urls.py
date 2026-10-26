from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.BookListView.as_filename if False else views.BookListView.as_view(), name='book_list'),
    path('book/<int:pk>/', views.BookDetailView.as_view(), name='book_detail'),
    path('book/add/', views.BookCreateView.as_view(), name='book_create'),
    path('book/<int:pk>/edit/', views.BookUpdateView.as_view(), name='book_update'),
    path('book/<int:pk>/delete/', views.BookDeleteView.as_view(), name='book_delete'),

# Кошик
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:book_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:book_id>/', views.cart_remove, name='cart_remove'),

    # Замовлення та оплата
    path('order/create/', views.order_create, name='order_create'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),
]