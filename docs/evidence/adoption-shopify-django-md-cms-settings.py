"""Overlay: adopt dsadmin in shopify-django-md-cms without touching its code."""
import os
os.environ.setdefault("DJANGO_SECRET_KEY", "overlay")
os.environ.setdefault("DJANGO_SECRET", "overlay-secret")
os.environ.setdefault("DJANGO_DEBUG", "1")
os.environ.setdefault("SHOPIFY_API_KEY", "test-key")
os.environ.setdefault("SHOPIFY_API_SECRET", "test-secret")
from config.settings import *  # noqa

INSTALLED_APPS = ["dsadmin", "dsadmin.apps.AdminConfig"] + [a for a in INSTALLED_APPS if a != "django.contrib.admin"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": os.environ.get("OVERLAY_DB", ":memory:")}}
DSADMIN = {"THEME": "admin", "DARK_THEME": "nocturne", "SITE_HEADER": "PLT CMS"}
STORAGES = {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
