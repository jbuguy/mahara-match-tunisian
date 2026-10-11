"""In-process request counters. They reset on restart and are not shared between workers."""

import time
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock


@dataclass
class RouteStats:
    requests: int = 0
    refusals: int = 0  # 4xx: the caller sent something wrong
    errors: int = 0    # 5xx: the module itself failed
    total_ms: float = 0.0
    max_ms: float = 0.0


class Metrics:
    """Counters kept per route template, never per URL: ids must not create buckets."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._routes: dict[str, RouteStats] = defaultdict(RouteStats)
        self.started_at = time.time()

    def record(self, route: str, status_code: int, duration_ms: float) -> None:
        with self._lock:  # several requests can finish at the same instant
            stats = self._routes[route]
            stats.requests += 1
            stats.total_ms += duration_ms
            stats.max_ms = max(stats.max_ms, duration_ms)
            if status_code >= 500:
                stats.errors += 1
            elif status_code >= 400:
                stats.refusals += 1

    def uptime_seconds(self) -> float:
        return round(time.time() - self.started_at, 1)

    def totals(self) -> tuple[int, int, int]:
        with self._lock:
            return (
                sum(stats.requests for stats in self._routes.values()),
                sum(stats.refusals for stats in self._routes.values()),
                sum(stats.errors for stats in self._routes.values()),
            )

    def snapshot(self) -> list[dict]:
        """Busiest routes first: that is the order an admin reads them in."""
        with self._lock:
            return [
                {
                    "route": route,
                    "requests": stats.requests,
                    "refusals": stats.refusals,
                    "errors": stats.errors,
                    "avg_ms": round(stats.total_ms / stats.requests, 2) if stats.requests else 0.0,
                    "max_ms": round(stats.max_ms, 2),
                }
                for route, stats in sorted(
                    self._routes.items(), key=lambda item: item[1].requests, reverse=True
                )
            ]


METRICS = Metrics()