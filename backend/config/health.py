from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from config.platform_mode import platform_mode_payload


@csrf_exempt
def health_check(request):
    """Lightweight liveness/readiness probe for load balancers and uptime monitors."""
    database_ok = True
    try:
        connections["default"].cursor().execute("SELECT 1")
    except OperationalError:
        database_ok = False

    healthy = database_ok
    payload = {
        "status": "ok" if healthy else "degraded",
        "database": database_ok,
        **platform_mode_payload(),
    }
    return JsonResponse(payload, status=200 if healthy else 503)
