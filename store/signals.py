import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from .models import Book, Category

logger = logging.getLogger(__name__)


@receiver([post_save, post_delete], sender=Book)
def invalidate_book_cache(sender, instance, **kwargs):
    """
    Інвалідація кешу деталей книги та списку при оновленні або видаленні.
    """
    cache_key = f"book_detail_{instance.id}"
    cache.delete(cache_key)
    # Також очищаємо загальні ключі списків книг
    cache.delete("books_list_cache")
    logger.info(f"Invalidated cache for book id={instance.id} (key: {cache_key})")


@receiver([post_save, post_delete], sender=Category)
def invalidate_category_cache(sender, instance, **kwargs):
    """
    Інвалідація кешу категорій при створенні/зміні/видаленні.
    """
    cache.delete("categories_all_cache")
    logger.info(f"Invalidated cache for category id={instance.id}")
