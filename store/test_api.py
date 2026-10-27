import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from store.models import Category, Book, Order
from store.factories import CategoryFactory, BookFactory, OrderFactory

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        username="apiclient_user",
        email="api_user@example.com",
        password="ValidPassword123!"
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="api_admin",
        email="api_admin@example.com",
        password="AdminPassword123!"
    )


@pytest.fixture
def auth_client(api_client, test_user):
    api_client.force_authenticate(user=test_user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


# =============================================================================
# 1. JWT Authentication Endpoints Tests (4 тести)
# =============================================================================

@pytest.mark.django_db
class TestJWTAuthentication:
    def test_jwt_obtain_pair_success(self, api_client, test_user):
        url = reverse('token_obtain_pair')
        response = api_client.post(url, {
            'username': test_user.username,
            'password': 'ValidPassword123!'
        })
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_jwt_obtain_pair_invalid_credentials(self, api_client, test_user):
        url = reverse('token_obtain_pair')
        response = api_client.post(url, {
            'username': test_user.username,
            'password': 'WrongPassword999!'
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_jwt_token_refresh(self, api_client, test_user):
        obtain_res = api_client.post(reverse('token_obtain_pair'), {
            'username': test_user.username,
            'password': 'ValidPassword123!'
        })
        refresh_token = obtain_res.data['refresh']

        refresh_url = reverse('token_refresh')
        response = api_client.post(refresh_url, {'refresh': refresh_token})
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_jwt_token_verify(self, api_client, test_user):
        obtain_res = api_client.post(reverse('token_obtain_pair'), {
            'username': test_user.username,
            'password': 'ValidPassword123!'
        })
        access_token = obtain_res.data['access']

        verify_url = reverse('token_verify')
        response = api_client.post(verify_url, {'token': access_token})
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# 2. Categories API Tests (4 тести)
# =============================================================================

@pytest.mark.django_db
class TestCategoryAPI:
    def test_category_list_public_access(self, api_client):
        CategoryFactory(name="Science", slug="science")
        response = api_client.get(reverse('api-category-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_category_detail_public_access(self, api_client):
        cat = CategoryFactory(name="History", slug="history")
        response = api_client.get(reverse('api-category-detail', args=[cat.id]))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == "History"

    def test_category_create_forbidden_for_regular_user(self, auth_client):
        response = auth_client.post(reverse('api-category-list'), {
            'name': 'Fantasy',
            'slug': 'fantasy'
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_category_create_success_for_admin(self, admin_client):
        response = admin_client.post(reverse('api-category-list'), {
            'name': 'Biography',
            'slug': 'biography'
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Category.objects.filter(slug='biography').exists()


# =============================================================================
# 3. Books API, Pagination & Filtering Tests (7 тестів)
# =============================================================================

@pytest.mark.django_db
class TestBookAPI:
    def test_book_list_public_access(self, api_client):
        BookFactory(title="Python Book")
        response = api_client.get(reverse('api-book-list'))
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_book_pagination_20_items(self, api_client):
        category = CategoryFactory()
        BookFactory.create_batch(25, category=category)

        response = api_client.get(reverse('api-book-list'))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 25
        assert len(response.data['results']) == 20
        assert response.data['next'] is not None

    def test_book_filter_by_category_slug(self, api_client):
        cat_python = CategoryFactory(name="Python", slug="python")
        cat_java = CategoryFactory(name="Java", slug="java")
        BookFactory(title="Django Guide", category=cat_python)
        BookFactory(title="Spring Guide", category=cat_java)

        response = api_client.get(f"{reverse('api-book-list')}?category__slug=python")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['title'] == "Django Guide"

    def test_book_search_filter(self, api_client):
        BookFactory(title="Architecture Patterns with Python")
        BookFactory(title="Learning SQL")

        response = api_client.get(f"{reverse('api-book-list')}?search=Architecture")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert "Architecture" in response.data['results'][0]['title']

    def test_book_detail_nested_category(self, api_client):
        cat = CategoryFactory(name="DevOps", slug="devops")
        book = BookFactory(title="Docker Deep Dive", category=cat)

        response = api_client.get(reverse('api-book-detail', args=[book.id]))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['category']['name'] == "DevOps"

    def test_book_create_forbidden_for_regular_user(self, auth_client):
        cat = CategoryFactory()
        response = auth_client.post(reverse('api-book-list'), {
            'title': 'Hacking Pro',
            'author': 'Unknown',
            'price': '19.99',
            'stock': 10,
            'category_id': cat.id
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_book_create_success_for_admin(self, admin_client):
        cat = CategoryFactory()
        response = admin_client.post(reverse('api-book-list'), {
            'title': 'DRF Mastery',
            'author': 'Author Name',
            'description': 'Comprehensive guide',
            'price': '35.50',
            'stock': 15,
            'category_id': cat.id
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Book.objects.filter(title='DRF Mastery').exists()


# =============================================================================
# 4. Orders API & Permissions (IsOwnerOrReadOnly) Tests (4 тести)
# =============================================================================

@pytest.mark.django_db
class TestOrderPermissionsAndAPI:
    def test_unauthenticated_cannot_view_orders(self, api_client):
        response = api_client.get(reverse('api-order-list'))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_can_view_only_own_orders(self, api_client, test_user):
        other_user = User.objects.create_user(username="other_user", password="pwd")
        OrderFactory(user=test_user, first_name="Mine")
        OrderFactory(user=other_user, first_name="Theirs")

        api_client.force_authenticate(user=test_user)
        response = api_client.get(reverse('api-order-list'))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['first_name'] == "Mine"

    def test_user_cannot_delete_other_user_order(self, api_client, test_user):
        other_user = User.objects.create_user(username="stranger", password="pwd")
        stranger_order = OrderFactory(user=other_user)

        api_client.force_authenticate(user=test_user)
        response = api_client.delete(reverse('api-order-detail', args=[stranger_order.id]))
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]

    def test_admin_can_view_all_orders(self, admin_client, test_user):
        other_user = User.objects.create_user(username="client_b", password="pwd")
        OrderFactory(user=test_user)
        OrderFactory(user=other_user)

        response = admin_client.get(reverse('api-order-list'))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2


# =============================================================================
# 5. Cart API Endpoints Tests (4 тести)
# =============================================================================

@pytest.mark.django_db
class TestCartAPI:
    def test_cart_get_empty(self, api_client):
        response = api_client.get(reverse('api-cart-list'))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_items'] == 0
        assert response.data['total_cost'] == '0.00'

    def test_cart_add_item_success(self, api_client):
        book = BookFactory(price=15.00, stock=5)
        response = api_client.post(reverse('api-cart-add'), {
            'book_id': book.id,
            'quantity': 2
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_items'] == 2

    def test_cart_add_exceeding_stock_fails(self, api_client):
        book = BookFactory(stock=2)
        response = api_client.post(reverse('api-cart-add'), {
            'book_id': book.id,
            'quantity': 5
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Not enough stock' in response.data['error']

    def test_cart_clear(self, api_client):
        book = BookFactory(stock=10)
        api_client.post(reverse('api-cart-add'), {'book_id': book.id, 'quantity': 1})
        response = api_client.post(reverse('api-cart-clear'))
        assert response.status_code == status.HTTP_200_OK

        cart_res = api_client.get(reverse('api-cart-list'))
        assert cart_res.data['total_items'] == 0


# =============================================================================
# 6. OpenAPI Documentation & CORS Headers Tests (3 тести)
# =============================================================================

@pytest.mark.django_db
class TestAPIDocumentationAndCORS:
    def test_openapi_schema_endpoint(self, api_client):
        response = api_client.get(reverse('schema'))
        assert response.status_code == status.HTTP_200_OK
        assert 'openapi' in response.data or 'paths' in response.data

    def test_swagger_ui_endpoint(self, api_client):
        response = api_client.get(reverse('swagger-ui'))
        assert response.status_code == status.HTTP_200_OK
        assert b"swagger-ui" in response.content.lower()

    def test_cors_headers_present(self, api_client):
        response = api_client.get(
            reverse('api-book-list'),
            HTTP_ORIGIN='http://localhost:3000'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.headers.get('Access-Control-Allow-Origin') == '*'