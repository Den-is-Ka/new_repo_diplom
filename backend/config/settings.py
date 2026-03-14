import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# -------------------------
# Base
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent  # .../backend
PROJECT_DIR = BASE_DIR.parent  # .../container_configurator (корень проекта)

# Загружаем .env с ПЕРЕЗАПИСЬЮ существующих переменных
load_dotenv(PROJECT_DIR / ".env", override=True)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")

# -------------------------
# Debug (ТОЛЬКО через env)
# -------------------------
debug_value = os.getenv("DJANGO_DEBUG", "0").strip().lower()
DEBUG = debug_value in ("1", "true", "yes", "on", "t")

# -------------------------
# Hosts / CSRF
# -------------------------
default_hosts = "127.0.0.1,localhost,0.0.0.0"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", default_hosts).split(",")
    if h.strip()
]

# 🔧 удобно для UI/демо (если где-то забудешь слэш)
APPEND_SLASH = True

# -------------------------
# Apps
# -------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    "whitenoise.runserver_nostatic",
    "users",
    "catalog",
    "configurator",
    "orders",
    "notifications",
    "ui",
]

AUTH_USER_MODEL = "users.User"

# -------------------------
# Middleware
# -------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# -------------------------
# Database — используем переменные из .env
# -------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': os.environ.get('POSTGRES_HOST'),
        'PORT': os.environ.get('POSTGRES_PORT'),
    }
}

# Для отладки — раскомментируй, чтобы увидеть значения
print("DB_NAME:", os.environ.get('POSTGRES_DB'))
print("DB_USER:", os.environ.get('POSTGRES_USER'))
print("DB_PASSWORD:", os.environ.get('POSTGRES_PASSWORD'))

# Для обратной совместимости (если где-то используются старые имена)
DB_NAME = DATABASES['default']['NAME']
DB_USER = DATABASES['default']['USER']
DB_PASSWORD = DATABASES['default']['PASSWORD']
DB_HOST = DATABASES['default']['HOST']
DB_PORT = DATABASES['default']['PORT']

# -------------------------
# Password validation
# -------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -------------------------
# I18N / TZ
# -------------------------
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# -------------------------
# Static / Media
# -------------------------
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------
# DRF
# -------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "config.api_exceptions.custom_exception_handler",
}

# -------------------------
# JWT
# -------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CONFIG_REQUIRED_MODULE_CODES = []
CONFIG_REQUIRED_CATEGORY_CODES = []

# -------------------------
# OpenAPI / Swagger (drf-spectacular)
# -------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Diplom • Container Configurator API",
    "DESCRIPTION": (
        "Backend для конфигуратора контейнерных решений.\n\n"
        "Ключевые сценарии:\n"
        "- Конфигурирование (категории/модули/инженерка, расчёт цены)\n"
        "- Submit конфигурации → создание Order со snapshot и фиксацией цены\n"
        "- Жизненный цикл заказа (NEW → IN_REVIEW → APPROVED → IN_PRODUCTION → COMPLETED / REJECTED)\n"
        "- Роли: client / admin (staff) / manufacturer (group)\n"
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "auth", "description": "JWT авторизация"},
        {
            "name": "catalog",
            "description": "Каталог: категории, модули, инженерные опции",
        },
        {
            "name": "configurator",
            "description": "Конфигурации: create/update/validate/set_engineering/submit",
        },
        {
            "name": "orders",
            "description": "Заказы: list/retrieve/history/status lifecycle",
        },
        {"name": "ui", "description": "HTML/UI endpoints (если используются)"},
    ],
}

# -------------------------
# Email
# -------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@diplom.local")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)

EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[Diplom] ")

MANUFACTURER_NOTIFY_EMAIL = os.getenv(
    "MANUFACTURER_NOTIFY_EMAIL", "manufacturer@diplom.local"
)

EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))