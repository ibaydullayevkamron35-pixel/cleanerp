"""CleanERP sozlamalari.

Ishlab chiqish uchun SQLite, ishga tushirishda PostgreSQL (muhit o'zgaruvchilari orqali).
"""
import datetime
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-only-secret-key-change-me-in-production')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # CleanERP
    'accounts',
    'core',
    'crm',
    'facilities',
    'orders',
    'hr',
    'inventory',
    'finance',
    'quality',
    'reports',
    'website',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.nav',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

if os.environ.get('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ['DB_NAME'],
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- Amazon S3 (obyektli saqlash). Kalitlar kodda yo'q: EC2 ga biriktirilgan IAM role ishlatiladi ---
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'ap-southeast-2')
if AWS_STORAGE_BUCKET_NAME:
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': {'bucket_name': AWS_STORAGE_BUCKET_NAME, 'region_name': AWS_S3_REGION_NAME,
                        'default_acl': None, 'querystring_auth': True, 'file_overwrite': False},
        },
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'landing'

from django.contrib.messages import constants as _messages  # noqa: E402

MESSAGE_TAGS = {_messages.ERROR: 'danger'}

# Xavfsizlik (ishga tushirishda DJANGO_DEBUG=0 qilinganda yoqiladi)
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # nginx orqasida HTTPS ni tanish uchun

# --- CleanERP sozlamalari ---
WORK_START = datetime.time(9, 0)  # shundan keyin kelgan xodim "kechikdi" deb belgilanadi

COMPANY = {
    'name': 'CleanERP',
    'tagline': "Toza makon — sog'lom biznes",
    'phone': '+998 90 000 00 00',   # o'zingizning raqamingizga almashtiring
    'email': 'info@cleanerp.example',
    'address': 'Toshkent shahri',
    'work_hours': '09:00 — 18:00',
}
