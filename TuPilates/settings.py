import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv


load_dotenv()



# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent


# Detectar entorno
ENVIRONMENT = os.environ.get("ENVIRONMENT", "local")  # "local" o "production"
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

# Solo activar cookies seguras en producción
SESSION_COOKIE_SECURE = not IS_LOCAL
CSRF_COOKIE_SECURE = not IS_LOCAL

# Aplicaciones instaladas - AGREGAR corsheaders
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',  # ← NUEVO
    'Pilapp',
]

# Middleware - AGREGAR CorsMiddleware AL PRINCIPIO
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # ← NUEVO - DEBE IR PRIMERO
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CONFIGURACIÓN CORS - AGREGAR AL FINAL
CORS_ALLOWED_ORIGINS = [
    "https://mcp-pilates-production.up.railway.app",  # Tu servidor MCP
    "https://pilatesmacp-client-production.up.railway.app",  # Tu cliente
]

# Alternativamente, para desarrollo puedes usar (MENOS SEGURO):
if IS_LOCAL:
    CORS_ALLOW_ALL_ORIGINS = True

# Configurar headers CORS específicos
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_HEADERS = [
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

# Configuración de URLs
ROOT_URLCONF = 'TuPilates.urls'

# Plantillas
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Para templates globales si los necesitás
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

# WSGI
WSGI_APPLICATION = 'TuPilates.wsgi.application'

# Base de Datos - Railway en ambos casos, pero con SSL solo en producción
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=not IS_LOCAL  # SSL solo en producción
        )
    }
else:
    # Fallback para desarrollo sin variable de entorno
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'railway',
            'USER': 'postgres',
            'PASSWORD': os.environ.get("DB_PASSWORD", ""),
            'HOST': os.environ.get("DB_HOST", ""),
            'PORT': os.environ.get("DB_PORT", "5432"),
            'OPTIONS': {} if IS_LOCAL else {'sslmode': 'require'},
        }
    }

# Validaciones de contraseñas
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-py'  # Cambiado a español Paraguay
TIME_ZONE = 'America/Asuncion'  # Tu timezone
USE_I18N = True
USE_TZ = True

# Archivos estáticos
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging
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


# Auto field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
