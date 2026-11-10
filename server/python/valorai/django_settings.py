import os

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "valorai-development-only")
DEBUG = False
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "valorai.django_urls"
INSTALLED_APPS: list[str] = []
MIDDLEWARE: list[str] = []
TIME_ZONE = "UTC"
USE_TZ = False
DATABASES = {
    "default": {
        "ENGINE": "django_cf.db.backends.d1",
        "CLOUDFLARE_BINDING": "DB",
    }
}
