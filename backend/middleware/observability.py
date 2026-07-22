import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger("bitsagenda.requests")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        request.state.request_id = request_id

        inicio = time.perf_counter()

        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            duracao_ms = round((time.perf_counter() - inicio) * 1000, 2)

            logger.exception(
                "request_error",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duracao_ms,
                    "client_ip": request.client.host if request.client else None,
                },
            )

            raise

        duracao_ms = round((time.perf_counter() - inicio) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = str(duracao_ms)

        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duracao_ms,
                "client_ip": request.client.host if request.client else None,
            },
        )

        return response
