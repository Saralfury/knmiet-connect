import json
import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.metrics import metrics, request_metrics_context


logger = logging.getLogger("knmiet.request")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.propagate = False


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", "")[:128] or str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.actor_id = None
        request_context = {"security_event_type": None}
        context_token = request_metrics_context.set(request_context)
        started_at = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration = time.perf_counter() - started_at
            route = request.scope.get("route")
            route_name = getattr(route, "path", request.url.path)
            event_type = request_context["security_event_type"]
            metrics.record_request(route_name, status_code, duration)
            logger.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "method": request.method,
                        "route": route_name,
                        "status": status_code,
                        "duration_ms": round(duration * 1000, 3),
                        "actor_id": getattr(request.state, "actor_id", None),
                        "security_event_type": event_type,
                    },
                    separators=(",", ":"),
                )
            )
            request_metrics_context.reset(context_token)
