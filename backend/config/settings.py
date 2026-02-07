import os
import sys
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
# PROJECT_ROOT РЅРµ РЅСѓР¶РµРЅ Р±РѕР»СЊС€Рµ - СѓР±РёСЂР°РµРј

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")

# РќР°СЃС‚СЂРѕР№РєР° DEBUG - РїСЂРёРЅСѓРґРёС‚РµР»СЊРЅРѕ True РґР»СЏ СЂР°Р·СЂР°Р±РѕС‚РєРё
if 'runserver' in sys.argv or 'migrate' in sys.argv or 'collectstatic' in sys.argv:
    DEBUG = True
else:
    debug_value = os.getenv("DJANGO_DEBUG", "false").strip().lower()
    DEBUG = debug_value in ("1", "true", "yes", "on", "t")

print(f"DEBUG mode: {DEBUG}")
print(f"BASE_DIR: {BASE_DIR}")

# ALLOWED_HOSTS СЃ СѓС‡РµС‚РѕРј Docker
default_hosts = "127.0.0.1,localhost,0.0.0.0"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", default_hosts).split(",")
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS if h.strip()]
print(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")

# Application definition

INSTALLED_APPS = [

# Пользовательская модель


    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # РЎС‚РѕСЂРѕРЅРЅРёРµ РїСЂРёР»РѕР¶РµРЅРёСЏ
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    "whitenoise.runserver_nostatic",
    # Р›РѕРєР°Р»СЊРЅС‹Рµ РїСЂРёР»РѕР¶РµРЅРёСЏ
    "users",
    "catalog",
    "configurator",
    "orders",
    "notifications",
]

# Пользовательская модель
AUTH_USER_MODEL = 'users.User'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Р”РѕР±Р°РІР»СЏРµРј РґР»СЏ РїСЂРѕРґР°РєС€РµРЅР°
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # Р”РѕР±Р°РІР»СЏРµРј РїР°РїРєСѓ templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "diplom_db"),
        "USER": os.getenv("POSTGRES_USER", "diplom_user"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "diplom_pass"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'ru-ru'  # РњРµРЅСЏРµРј РЅР° СЂСѓСЃСЃРєРёР№

TIME_ZONE = 'Europe/Moscow'  # РњРµРЅСЏРµРј РЅР° РјРѕСЃРєРѕРІСЃРєРѕРµ РІСЂРµРјСЏ

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# РС‰РµРј СЃС‚Р°С‚РёРєСѓ С‚РѕР»СЊРєРѕ РІ /app/static
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Р”Р»СЏ РїСЂРѕРґР°РєС€РµРЅР° (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

print(f"STATIC_ROOT: {STATIC_ROOT}")
print(f"STATICFILES_DIRS: {STATICFILES_DIRS}")

# РњРµРґРёР° С„Р°Р№Р»С‹ (Р·Р°РіСЂСѓР¶РµРЅРЅС‹Рµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏРјРё)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# РџРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєР°СЏ РјРѕРґРµР»СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ (РµСЃР»Рё РµСЃС‚СЊ)

# Django REST Framework settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",  # Р”РѕР±Р°РІР»СЏРµРј РґР»СЏ Р°РґРјРёРЅРєРё
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",  # РњРѕР¶РЅРѕ РёР·РјРµРЅРёС‚СЊ РЅР° IsAuthenticated РїРѕР·Р¶Рµ
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # РџР°РіРёРЅР°С†РёСЏ (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ)
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# Swagger/OpenAPI settings
SPECTACULAR_SETTINGS = {
    "TITLE": "Diplom Container Configurator API",
    "DESCRIPTION": "API РґР»СЏ РєРѕРЅС„РёРіСѓСЂР°С‚РѕСЂР° РѕР±РѕСЂСѓРґРѕРІР°РЅРёСЏ Рё СЂР°СЃС‡РµС‚Р° СЃС‚РѕРёРјРѕСЃС‚Рё РєРѕРЅС‚РµР№РЅРµСЂР°",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r'/api/',

    # РћРїС†РёРѕРЅР°Р»СЊРЅРѕ: РєСЂР°СЃРёРІС‹Р№ РёРЅС‚РµСЂС„РµР№СЃ
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
    },

    # РћРїС†РёРѕРЅР°Р»СЊРЅРѕ: РїРѕРґРґРµСЂР¶РєР° JWT РІ Swagger
    "SECURITY": [{"Bearer": []}],
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header"
        }
    },
}

# CORS Settings
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
).split(",")
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ALLOWED_ORIGINS if origin.strip()]

# Р”Р»СЏ РїСЂРѕРґР°РєС€РµРЅР° С‚Р°РєР¶Рµ РЅСѓР¶РЅРѕ РЅР°СЃС‚СЂРѕРёС‚СЊ:
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS.copy() if DEBUG else []

# Р Р°Р·СЂРµС€Р°РµРј РѕС‚РїСЂР°РІРєСѓ cookies С‡РµСЂРµР· CORS
CORS_ALLOW_CREDENTIALS = True

# Р Р°Р·СЂРµС€Р°РµРј РІСЃРµ РјРµС‚РѕРґС‹
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Р Р°Р·СЂРµС€Р°РµРј РІСЃРµ Р·Р°РіРѕР»РѕРІРєРё
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Email settings (РґР»СЏ СѓРІРµРґРѕРјР»РµРЅРёР№)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', '1') == '1'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@diplom.local')

# Telegram Bot settings (РґР»СЏ СѓРІРµРґРѕРјР»РµРЅРёР№ РїСЂРѕРёР·РІРѕРґРёС‚РµР»СЏ)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'] if DEBUG else ['console'],
        'level': 'DEBUG' if DEBUG else 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'] if DEBUG else ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'handlers': ['console'],
        },
    },
}



