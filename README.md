[![Django CI](https://github.com/DariiaMiroshn/bookstore_project/actions/workflows/django.yml/badge.svg)](https://github.com/DariiaMiroshn/bookstore_project/actions/workflows/django.yml)
[![Coverage](https://img.shields.io/badge/coverage-92%25-brightgreen)](https://github.com/DariiaMiroshn/bookstore_project)

# 📚 Bookstore & Warehouse Microservices Architecture

Комплексна мікросервісна система електронної комерції на Django з інтеграцією ізольованого сервісу складу в реальному часі, платіжною системою Stripe, асинхронними чергами Celery, контейнеризацією через Docker Compose та покриттям тестами 92%.

---

## 🏛️ Архітектура системи

1. **Bookstore Service (`Project A`)** — Django 5, DRF:
   - Каталог книг, пошук, фільтрація, кошик покупок (Cart).
   - Оформлення замовлення (Checkout) та оплата через Stripe Checkout Session.
   - Сповіщення та фонові задачі через Celery (email-підтвердження, звіти).
   - Інтернаціоналізація (i18n): підтримка англійської (`EN`) та української (`UK`) мов.
   - Інтеграція зі складом через відмовостійкий HTTP-клієнт (`WarehouseClient`) з JWT-автентифікацією.

2. **Warehouse Service (`Project B`)** — Django 5, DRF:
   - Ізольований мікросервіс складського обліку залишків у режимі реального часу.
   - Двоетапний життєвий цикл резервування: створення резерву (`/reserve/`), підтвердження списання після оплати (`/confirm/`), зняття резерву при скасуванні (`/cancel/`).
   - Автентифікація сервісних акаунтів через SimpleJWT.

3. **Інфраструктура:**
   - **Nginx:** Зворотний проксі (Reverse Proxy), єдина точка входу на порту `8080` та роздача статики.
   - **PostgreSQL 15:** Реляційна база даних.
   - **Redis 7:** Кеш та брокер повідомлень для Celery.
   - **Celery Worker & Celery Beat:** Фонова обробка завдань та планувальник періодичних тасків.

---

## 🔄 Схема взаємодії під час замовлення

```text
[ Клієнт ] ---> [ Nginx (:8080) ] ---> [ Bookstore Service ] ---> [ Stripe API ]
                                                |
                                         (HTTP / JWT Auth)
                                                |
                                                v
                                     [ Warehouse Service (:8001) ] ---> [ DB: Склад ]