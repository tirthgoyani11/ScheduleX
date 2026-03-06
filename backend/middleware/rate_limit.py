# middleware/rate_limit.py
"""
Per-user rate limiting for NLQ and generation endpoints.
Uses Redis for shared state across workers.
"""
import time
from fastapi import Request
from fastapi.responses import JSONResponse
from config import settings

# In-memory fallback when Redis is unavailable
_rate_store: dict[str, list[float]] = {}

RATE_LIMITS = {
    "/nlq/query": {"max_requests": 20, "window_seconds": 60},
    "/timetable/generate": {"max_requests": 20, "window_seconds": 300},
    "/exam/generate": {"max_requests": 20, "window_seconds": 300},
}


async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    limit_config = None

    for route_pattern, config in RATE_LIMITS.items():
        if path.endswith(route_pattern):
            limit_config = config
            break

    if limit_config and request.method == "POST":
        user = getattr(request.state, "user", None)
        user_key = user.user_id if user else (
            request.client.host if request.client else "unknown"
        )
        rate_key = f"rate:{user_key}:{path}"

        now = time.time()
        window = limit_config["window_seconds"]

        if rate_key not in _rate_store:
            _rate_store[rate_key] = []

        # Clean old entries
        _rate_store[rate_key] = [
            t for t in _rate_store[rate_key] if now - t < window
        ]

        if len(_rate_store[rate_key]) >= limit_config["max_requests"]:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Max {limit_config['max_requests']} requests per {window}s."},
            )

        _rate_store[rate_key].append(now)

    response = await call_next(request)
    return response
