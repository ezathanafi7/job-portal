from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest
from ninja import NinjaAPI, Schema

from apps.core.exceptions import register_exception_handlers

api = NinjaAPI(
    title="Job Portal API",
    version="1.0.0",
    description="Main service: accounts, companies, jobs, applications, career fair events.",
    urls_namespace="api-v1",
    docs_url="/docs" if settings.API_DOCS_ENABLED else None,
)

register_exception_handlers(api)


# ---------------------------------------------------------------------------
# Health check: used later by Docker and the hosting platform to know the app is alive
# ---------------------------------------------------------------------------


class HealthOut(Schema):
    status: str
    database: str
    cache: str


@api.get(
    "/health",
    response={200: HealthOut, 503: HealthOut},
    tags=["system"],
    summary="Is the app and its database working?",
)
def health(request: HttpRequest):
    checks = {"database": "ok", "cache": "ok"}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        checks["database"] = "error"

    try:
        cache.set("health-check", "ok", timeout=5)
        if cache.get("health-check") != "ok":
            checks["cache"] = "error"
    except Exception:
        checks["cache"] = "error"

    healthy = all(value == "ok" for value in checks.values())
    # 503 = "Service Unavailable": tells load balancers not to send traffic here
    return (200 if healthy else 503), {"status": "ok" if healthy else "degraded", **checks}

