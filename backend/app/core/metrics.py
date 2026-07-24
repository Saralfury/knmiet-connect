from collections import Counter
from contextvars import ContextVar
from dataclasses import dataclass, field


request_metrics_context: ContextVar[dict[str, str | None] | None] = ContextVar(
    "request_metrics_context",
    default=None,
)


@dataclass
class MetricsRegistry:
    request_count: int = 0
    total_latency_seconds: float = 0.0
    status_counts: Counter[str] = field(default_factory=Counter)
    route_counts: Counter[str] = field(default_factory=Counter)
    security_counts: Counter[str] = field(default_factory=Counter)

    def record_request(self, route: str, status: int, duration: float) -> None:
        self.request_count += 1
        self.total_latency_seconds += duration
        self.status_counts[str(status)] += 1
        self.route_counts[route] += 1

    def record_security_event(self, event_type: str) -> None:
        context = request_metrics_context.get()
        if context is not None:
            context["security_event_type"] = event_type
        self.security_counts[event_type] += 1

    def snapshot(self) -> dict[str, object]:
        average = (
            self.total_latency_seconds / self.request_count
            if self.request_count
            else 0.0
        )
        return {
            "request_count": self.request_count,
            "average_latency_ms": round(average * 1000, 3),
            "status_counts": dict(self.status_counts),
            "route_counts": dict(self.route_counts),
            "security_counts": dict(self.security_counts),
        }


metrics = MetricsRegistry()
