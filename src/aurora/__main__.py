"""Entry point: ``python -m aurora`` starts the API with uvicorn."""

from __future__ import annotations

import errno
import socket
import sys

import uvicorn

from .config import get_settings


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError as exc:
            return exc.errno == errno.EADDRINUSE
    return False


def main() -> int:
    settings = get_settings()
    if _port_in_use(settings.api_host, settings.api_port):
        print(
            f"[aurora] ERRO: a porta {settings.api_port} já está em uso em {settings.api_host}. "
            "Defina outra porta com API_PORT no .env (ex.: API_PORT=8080) ou pare o processo "
            f"que a usa (ex.: `lsof -i :{settings.api_port}`).",
            file=sys.stderr,
        )
        return 1
    uvicorn.run(
        "aurora.api.main:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
