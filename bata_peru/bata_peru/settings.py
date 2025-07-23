from pathlib import Path
import os

# Definir BASE_DIR antes de usarlo
BASE_DIR = Path(__file__).resolve().parent.parent

# STATIC_ROOT debe ir después de BASE_DIR
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Definir BASE_DIR antes de usarlo
BASE_DIR = Path(__file__).resolve().parent.parent

# STATIC_ROOT debe ir después de BASE_DIR
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# --- Configuración Channels para WebSocket local ---
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}
from pathlib import Path
import os

# Definir BASE_DIR antes de usarlo
BASE_DIR = Path(__file__).resolve().parent.parent

# Configuración de archivos estáticos y medios
from pathlib import Path
import os

# Definir BASE_DIR antes de usarlo
BASE_DIR = Path(__file__).resolve().parent.parent

# Configuración de archivos estáticos y medios
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

LOGIN_URL = '/login/'
# Resto de la configuración
SECRET_KEY = 'django-insecure-_akmxo)aw)&*v*8vr_qf$rwf8bjjs(a&*-9*pi&&mmsl2d-a_z'
DEBUG = True

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '[::1]',
    'afdadd7e4551.ngrok-free.app',
]

# Permitir CSRF desde el dominio de ngrok
CSRF_TRUSTED_ORIGINS = [
    'https://afdadd7e4551.ngrok-free.app',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'bata_peru.inventario',
    'bata_peru.users',
    'bata_peru.ventas',
    'tailwind',
]

ASGI_APPLICATION = 'bata_peru.asgi.application'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bata_peru.bata_peru.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # 👈 Muy importante
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'bata_peru.context_processors.admin_user_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'bata_peru.bata_peru.wsgi.application'

# Base de datos Postgress
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'dockerproject',
        'USER': 'myuser',
        'PASSWORD': 'mypassword',
        'HOST': 'localhost',  
        'PORT': '5432',  
    }
}

AUTH_USER_MODEL = 'users.UsuarioPersonalizado'

# Validación de contraseñas
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

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Lima'  # zona horaria de Perú
USE_TZ = True               
USE_I18N = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",  
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
