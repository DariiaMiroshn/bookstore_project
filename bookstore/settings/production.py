import os
from .base import *

# На продакшні DEBUG строго вимкнений
DEBUG = False

# Дозволені хости беремо зі змінних середовища або дозволяємо домени
ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS", "localhost,127.0.0.1,.onrender.com,.railway.app"
).split(",")

# WHITENOISE STATIC STORAGE

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# SECURITY HEADERS

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Якщо на хостингу є SSL/HTTPS (наприклад на Render/Railway)
if os.environ.get("ENVIRONMENT") == "production":
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
