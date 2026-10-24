"""Reusable OpenAPI response metadata; these declarations do not enforce behavior."""

from fastapi import status
from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: ErrorDetail


ETAG_HEADERS: dict[str, object] = {
    "ETag": {
        "description": (
            "Strong validator for this resource representation. Send it unchanged in If-Match."
        ),
        "schema": {"type": "string"},
        "example": '"5d23d9a6-4198-4fca-ae01-f962d7b71401"',
    },
}

CONDITIONAL_UPDATE_RESPONSES: dict[int | str, dict[str, object]] = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ErrorResponse,
        "description": "Malformed If-Match header. Use a quoted entity-tag, a list, or *.",
        "content": {
            "application/json": {
                "example": {
                    "detail": {
                        "code": "invalid_if_match",
                        "message": "Invalid If-Match header",
                    }
                }
            }
        },
    },
    status.HTTP_412_PRECONDITION_FAILED: {
        "model": ErrorResponse,
        "description": (
            "No strong tag matched, or the resource changed or was deleted before the "
            "operation completed. Retrieve its current state and reconcile before retrying."
        ),
        "content": {
            "application/json": {
                "example": {
                    "detail": {
                        "code": "precondition_failed",
                        "message": (
                            "The resource changed or was deleted; "
                            "reconcile its current state before retrying"
                        ),
                    }
                }
            }
        },
    },
    status.HTTP_428_PRECONDITION_REQUIRED: {
        "model": ErrorResponse,
        "description": "If-Match is required. Retrieve the resource and send its ETag.",
        "content": {
            "application/json": {
                "example": {
                    "detail": {
                        "code": "precondition_required",
                        "message": "Supply If-Match from the resource's ETag",
                    }
                }
            }
        },
    },
}

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
