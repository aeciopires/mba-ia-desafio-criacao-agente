"""Logging configuration focused on making root causes easy to find."""

import logging
import sys

_FORMAT = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger once, writing to stderr (captured by `docker compose logs`)."""
    root = logging.getLogger()
    if getattr(root, "_aurora_configured", False):
        root.setLevel(level.upper())
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_FORMAT))
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # Third-party loggers that are too chatty at INFO.
    for noisy in ("httpx", "httpcore", "google_genai.models", "aiosqlite", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    root._aurora_configured = True  # type: ignore[attr-defined]
