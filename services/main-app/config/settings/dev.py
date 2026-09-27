import logging

from apps.accounts.jwt_tokens import generate_rsa_keypair

from .base import *  # noqa: F403
from .base import JWT, REFRESH_COOKIE, SECRET_KEY, env

DEBUG = env.bool("DJANGO_DEBUG", default=True)

# A fixed fallback key is OK on your laptop only. prod.py refuses to start without a real one.
SECRET_KEY = SECRET_KEY or "dev-only-insecure-key-never-use-in-production"

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

API_DOCS_ENABLED = env.bool("API_DOCS_ENABLED", default=True)

# localhost uses plain HTTP, so the cookie can't require HTTPS in development.
REFRESH_COOKIE["SECURE"] = env.bool("AUTH_COOKIE_SECURE", default=False)

# If someone clones the project and hasn't generated keys yet, create temporary ones
# so the app still starts. (Everyone gets logged out whenever the server restarts.)
if not JWT["PRIVATE_KEY"] or not JWT["PUBLIC_KEY"]:
    logging.getLogger(__name__).warning(
        "JWT keys not set in .env; using temporary keys. "
        "Run `uv run python manage.py generate_jwt_keys` to fix this."
    )
    JWT["PRIVATE_KEY"], JWT["PUBLIC_KEY"] = generate_rsa_keypair()