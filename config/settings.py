import os
from pathlib import Path
from dotenv import load_dotenv
from django.utils.translation import gettext_lazy as _

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", default="")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", default=False)

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS").split(",")
CSRF_TRUSTED_ORIGINS = [u.strip() for u in os.environ.get("CSRF_TRUSTED_ORIGINS","").split(",") if u.strip()]

# Current DJANGO_ENVIRONMENT
ENVIRONMENT = os.environ.get("DJANGO_ENVIRONMENT", default="prod")

# Application definition

INSTALLED_APPS = [
    "jazzmin",
    "dal",
    "dal_select2",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'import_export',

    # local apps
    "museum",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    "django.middleware.locale.LocaleMiddleware",
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
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE"),
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
        "CONN_MAX_AGE": 600,
        "OPTIONS": {"connect_timeout": 5},

    }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "uz"
LANGUAGES = [
    ("uz", _("Oʻzbekcha")),
    ("ru", _("Русский")),
    ("en", _("English")),
    ("ar", _("العربيّة"))
]
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS =[BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / 'staticfiles/'

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/isc/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

BASE_URL = os.environ.get("BASE_URL", default="http://127.0.0.1:8000")
QR_TEXT_FONT_PATH = BASE_DIR / "static" / "museum" / "fonts" / "DejaVuSans.ttf"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

JAZZMIN_SETTINGS = {
    "site_title": "Museum Admin",
    "site_header": "Museum Admin",
    "site_brand": "Museum",
    "welcome_sign": "Добро пожаловать",
    "show_ui_builder": False,

    # Иконки моделей (чтобы было красиво)
    "icons": {
        "museum.Museum": "fas fa-landmark",
        "museum.MuseumBlock": "fas fa-layer-group",
        "museum.MuseumSection": "fas fa-sitemap",
        "museum.Exhibit": "fas fa-cube",
        "museum.ExhibitPhoto": "fas fa-images",
    },

    # Логотип и фавикон (по желанию)
    # "site_logo": "museum/img/logo.png",
    # "site_icon": "museum/img/favicon.png",

    # Меню — можно группировать
    "topmenu_links": [
        {"name": "Сайт", "url": "/", "permissions": ["museum.view_exhibit"]},
    ],
    "language_chooser": True,
}

JAZZMIN_UI_TWEAKS = {
    "theme": "darkly",            # Тёмная тема
    "dark_mode_theme": "darkly",
    "navbar": "navbar-dark",
    "accent": "accent-warning",   # Золотистые акценты (под музей)
    "sidebar": "sidebar-dark",
    "brand_colour": "navbar-dark",

    # Доп улучшения читаемости
    "related_modal_active": True,
    "body_small_text": False,
    "layout": "fixed",
    "sidebar_fixed": True,
    "sidebar_nav_small_text": False,
    "footer_fixed": False,
}

