from django.urls import path
from . import views

app_name = "store"

urlpatterns = [
    path(
        "",
        views.BookListView.as_filename if False else views.BookListView.as_view(),
        name="book_list",
    ),
    path("book/<int:pk>/", views.BookDetailView.as_view(), name="book_detail"),
    path("book/add/", views.BookCreateView.as_view(), name="book_create"),
    path("book/<int:pk>/edit/", views.BookUpdateView.as_view(), name="book_update"),
    path("book/<int:pk>/delete/", views.BookDeleteView.as_view(), name="book_delete"),
    # Кошик
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:book_id>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:book_id>/", views.cart_remove, name="cart_remove"),
    # Замовлення та оплата
    path("order/create/", views.order_create, name="order_create"),
    path("payment/success/", views.payment_success, name="payment_success"),
    path("payment/cancel/", views.payment_cancel, name="payment_cancel"),
    # Асинхронні views
    path("async/books/", views.async_book_list, name="async_book_list"),
    path(
        "async/books/<int:book_id>/", views.async_book_detail, name="async_book_detail"
    ),
    path(
        "async/category/<slug:category_slug>/",
        views.async_category_books,
        name="async_category_books",
    ),
]
