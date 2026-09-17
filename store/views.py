from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Book

# 1. Список книг з пагінацією (Public)
class BookListView(ListView):
    model = Book
    template_name = 'store/book_list.html'
    context_object_name = 'books'
    paginate_by = 4


# 2. Book details (Public)
class BookDetailView(DetailView):
    model = Book
    template_name = 'store/book_detail.html'
    context_object_name = 'book'


# 3. Create book (Requires 'store.add_book' permission)
class BookCreateView(PermissionRequiredMixin, CreateView):
    model = Book
    template_name = 'store/book_form.html'
    fields = ['title', 'author', 'category', 'price', 'description', 'stock']
    success_url = reverse_lazy('store:book_list')
    permission_required = 'store.add_book'


# 4. Update book (Requires 'store.change_book' permission)
class BookUpdateView(PermissionRequiredMixin, UpdateView):
    model = Book
    template_name = 'store/book_form.html'
    fields = ['title', 'author', 'category', 'price', 'description', 'stock']
    success_url = reverse_lazy('store:book_list')
    permission_required = 'store.change_book'


# 5. Delete book (Requires 'store.delete_book' permission)
class BookDeleteView(PermissionRequiredMixin, DeleteView):
    model = Book
    template_name = 'store/book_confirm_delete.html'
    success_url = reverse_lazy('store:book_list')
    permission_required = 'store.delete_book'