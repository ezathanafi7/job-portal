"""Settings for the live server. Every secret MUST come from environment variables."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import DATABASES, JWT, SECRET_KEY, env

DEBUG = False

# ---------------------------------------------------------------------------
# Refuse to start if something important is missing
# ---------------------------------------------------------------------------
if not SECRET_KEY or len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set to a long random value.")

if not JWT["PRIVATE_KEY"] or not JWT["PUBLIC_KEY"]:
    raise ImproperlyConfigured("JWT_PRIVATE_KEY and JWT_PUBLIC_KEY must be set in production.")

if "sqlite" in DATABASES["default"]["ENGINE"]:
    raise ImproperlyConfigured("DATABASE_URL must point to PostgreSQL in production.")

# ---------------------------------------------------------------------------
# HTTPS and browser security headers
# ---------------------------------------------------------------------------
# The proxy in front of Django (Caddy/Cloudflare) handles HTTPS and tells Django
# the original request was secure through this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # http:// -> https://

# HSTS: tells browsers "only ever use HTTPS for this site" for 1 year.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True               # stop browsers guessing file types
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"                          # can't be embedded in iframes (clickjacking)

# Cookies are only sent over HTTPS, and JavaScript can't read the session cookie.
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True