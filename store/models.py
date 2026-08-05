from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Category name")
    slug = models.SlugField(unique=True, verbose_name="URL-slug")

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200, verbose_name="Title")
    author = models.CharField(max_length=100, verbose_name="Author")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price")
    description = models.TextField(blank=True, verbose_name="Description")
    stock = models.PositiveIntegerField(default=0, verbose_name="Stock quantity")

    # Зв'язок "один-до-багатьох": у однієї категорії може бути багато книг
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='books',
        verbose_name="Category"
    )

    class Meta:
        verbose_name = "Book"
        verbose_name_plural = "Books"

    def __str__(self):
        return self.title