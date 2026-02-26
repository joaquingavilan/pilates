import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Detectar entorno
ENVIRONMENT = os.environ.get("ENVIRONMENT", "local")
IS_LOCAL = ENVIRONMENT == "local"

# Seguridad
SECRET_KEY = os.environ.get("SECRET_KEY", "clave-insegura-para-local")
DEBUG = IS_LOCAL or os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = ["*"] if IS_LOCAL else [
    "tupilates.up.railway.app",
    "localhost",
    "127.0.0.1",
]

CSRF_TRUSTED_ORIGINS = [
    "https://tupilates.up.railway.app",
]
if IS_LOCAL:
    CSRF_TRUSTED_ORIGINS += ["http://localhost:8000", "http://127.0.0.1:8000"]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = not IS_LOCAL
CSRF_COOKIE_SECURE = not IS_LOCAL

# Aplicaciones instaladas
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  
    'corsheaders', 
    'Pilapp',
]

# Middleware
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CONFIGURACIÓN CORS
CORS_ALLOWED_ORIGINS = [
    "https://mcp-pilates-production.up.railway.app",
    "https://pilatesmacp-client-production.up.railway.app",
]

if IS_LOCAL:
    CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_CREDENTIALS = True

# Configuración de URLs
ROOT_URLCONF = 'TuPilates.urls'

# Plantillas
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
            ],
        },
    },
]

WSGI_APPLICATION = 'TuPilates.wsgi.application'

# --- SECCIÓN DE BASE DE DATOS HÍBRIDA ---
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # PRIORIDAD 1: Si existe DATABASE_URL (Railway o .env), usar Postgres
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=not IS_LOCAL
        )
    }
else:
    # PRIORIDAD 2: Si no hay URL (Caso de hoy), usar SQLite local para que Postman funcione
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
# ------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-py'
TIME_ZONE = 'America/Asuncion'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG' if IS_LOCAL else 'INFO',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'