"""Reusable OpenAPI metadata for endpoints that enforce rate limits."""

from fastapi import status

RATE_LIMIT_RESPONSES: dict[int | str, dict[str, object]] = {
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "description": "Request rate limit exceeded.",
        "headers": {
            "Retry-After": {
                "description": "Seconds to wait before retrying, calculated by the rate limiter.",
                "schema": {"type": "integer", "minimum": 0},
                "example": 60,
            },
        },
    },
}
