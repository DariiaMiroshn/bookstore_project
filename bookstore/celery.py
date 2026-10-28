import os
from celery import Celery

# Вказуємо модуль налаштувань за замовчуванням для програми 'celery'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bookstore.settings")

app = Celery("bookstore")

# Зчитуємо конфігурацію з settings.py з префіксом CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматично знаходимо задачі (tasks.py) у всіх зареєстрованих додатках Django
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
