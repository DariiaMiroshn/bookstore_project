from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Book

# 1. Список книг з пагінацією
class BookListView(ListView):
    model = Book
    template_name = 'store/book_list.html'
    context_object_name = 'books'
    paginate_by = 4  # кількість книг на сторінку

# 2. Деталі книги
class BookDetailView(DetailView):
    model = Book
    template_name = 'store/book_detail.html'
    context_object_name = 'book'

# 3. Створення книги
class BookCreateView(CreateView):
    model = Book
    template_name = 'store/book_form.html'
    fields = ['title', 'author', 'category', 'price', 'description', 'stock']
    success_url = reverse_lazy('store:book_list')

# 4. Редагування книги
class BookUpdateView(UpdateView):
    model = Book
    template_name = 'store/book_form.html'
    fields = ['title', 'author', 'category', 'price', 'description', 'stock']
    success_url = reverse_lazy('store:book_list')

# 5. Видалення книги
class BookDeleteView(DeleteView):
    model = Book
    template_name = 'store/book_confirm_delete.html'
    success_url = reverse_lazy('store:book_list')