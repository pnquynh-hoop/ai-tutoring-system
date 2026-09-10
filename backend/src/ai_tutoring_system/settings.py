import os
from datetime import timedelta
from pathlib import Path
import cloudinary
import pymysql
from dotenv import load_dotenv

load_dotenv()

pymysql.install_as_MySQLdb()
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY")
DEBUG = os.getenv("DEBUG", "False").strip().lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "accounts.apps.AccountsConfig",
    "core.apps.CoreConfig",
    "courses.apps.CoursesConfig",
    "academics.apps.AcademicsConfig",
    "assignments.apps.AssignmentsConfig",
    "AI.apps.AiConfig",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "debug_toolbar",
    "django_cleanup.apps.CleanupConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

INTERNAL_IPS = [
    "127.0.0.1",
]

ROOT_URLCONF = "ai_tutoring_system.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ai_tutoring_system.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE"),
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", ""),
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", 60)),
        "CONN_HEALTH_CHECKS": True,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "vi"

TIME_ZONE = "Asia/Ho_Chi_Minh"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True,
)

AUTH_USER_MODEL = "accounts.User"

CHROMA_DB_PATH = os.environ.get("CHROMA_DB_PATH", str(BASE_DIR.parent / "chroma_db"))

MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR.parent))

RAG_CACHE_DIR = Path(os.environ.get("RAG_CACHE_DIR", BASE_DIR.parent / "rag_cache"))

RAG_OCR_ENABLED = (
    os.environ.get("RAG_OCR_ENABLED", "False").strip().lower() == "true"
)
RAG_OCR_DPI = int(os.environ.get("RAG_OCR_DPI", 150))
RAG_OCR_RPM = int(os.environ.get("RAG_OCR_RPM", 10))

RAG_ALLOW_GENERAL_KNOWLEDGE = (
    os.environ.get("RAG_ALLOW_GENERAL_KNOWLEDGE", "True").strip().lower() == "true"
)

RAG_MAX_DISTANCE = float(os.environ.get("RAG_MAX_DISTANCE", 0.62))

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "accounts.authentication.CookieJWTAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "ai": os.environ.get("AI_THROTTLE_RATE", "30/hour"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Tutoring Center API",
    "DESCRIPTION": "API documentation",
    "VERSION": "1.0.0",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
}

AUTH_COOKIE = {
    "ACCESS_NAME": "access_token",
    "REFRESH_NAME": "refresh_token",
    "SECURE": not DEBUG,
    "HTTP_ONLY": True,
    "SAMESITE": "Lax",
    "PATH": "/",
}

CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_TIME_LIMIT = 60 * 60

CLOSE_OVERDUE_EVERY_SECONDS = int(
    os.environ.get("CLOSE_OVERDUE_EVERY_SECONDS", 5 * 60)
)

CELERY_BEAT_SCHEDULE = {
    "close-overdue-attempts": {
        "task": "assignments.close_overdue_attempts",
        "schedule": CLOSE_OVERDUE_EVERY_SECONDS,
    },
}
