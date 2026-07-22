import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        campos_extras = [
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "client_ip",
        ]

        for campo in campos_extras:
            valor = getattr(record, campo, None)

            if valor is not None:
                payload[campo] = valor

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configurar_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    logging.getLogger("uvicorn.access").disabled = True
