import logging
import os
from logging.handlers import RotatingFileHandler

from .config import load_backend_env, writable_runtime_dir


load_backend_env()

LOG_DIR = os.getenv("LOG_DIR", os.path.join(writable_runtime_dir(), "logs"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "5242880"))
BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))


def configure_logging() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )

    app_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"),
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    app_handler.setFormatter(formatter)

    security_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "security.log"),
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    security_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    if not any(isinstance(handler, RotatingFileHandler) for handler in root_logger.handlers):
        root_logger.addHandler(app_handler)

    security_logger = logging.getLogger("assets_equity.security")
    security_logger.setLevel(LOG_LEVEL)
    if not security_logger.handlers:
        security_logger.addHandler(security_handler)
    security_logger.propagate = True
