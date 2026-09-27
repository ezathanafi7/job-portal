"""Settings for local development on your laptop."""

from .base import *  
from .base import SECRET_KEY, env

DEBUG = env.bool("DJANGO_DEBUG", default=True)

# A fixed fallback key is OK on your laptop only. prod.py refuses to start without a real one.
SECRET_KEY = SECRET_KEY or "dev-only-insecure-key-never-use-in-production"

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
API_DOCS_ENABLED = env.bool("API_DOCS_ENABLED", default=True)