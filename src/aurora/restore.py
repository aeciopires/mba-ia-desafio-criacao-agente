"""Restore command: resets reservations and visitors to the files in ``dados/``.

Usage:
    python -m aurora.restore            # reservations + visitors (sessions are kept)
    python -m aurora.restore --sessions # also deletes every conversation (make reset)
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys

from .config import get_settings
from .db.repository import Repository, RepositoryError
from .db.seed import seed
from .logging_setup import configure_logging

logger = logging.getLogger("aurora.restore")

_ADK_SESSION_TABLES = ("events", "sessions", "app_states", "user_states")


def clear_adk_sessions() -> int:
    """Delete every ADK session row, keeping the schema (safe while the API is running)."""
    settings = get_settings()
    path = settings.sessions_db_file
    if path is None:
        raise RuntimeError(
            "AURORA_SESSIONS_DB_URL não é SQLite; apague as sessões diretamente no seu banco."
        )
    if not path.exists():
        logger.info("Session database %s does not exist yet, nothing to delete", path)
        return 0
    conn = sqlite3.connect(path, timeout=30)
    try:
        existing = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        deleted = 0
        with conn:
            for table in _ADK_SESSION_TABLES:
                if table in existing:
                    deleted += conn.execute(f"DELETE FROM {table}").rowcount
        return deleted
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--sessions", action="store_true", help="also delete all conversations (sessions)"
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(settings.log_level)
    repo = Repository(settings.db_path)
    try:
        counts = seed(repo, settings.dados_dir)
        print(f"[restore] Dados iniciais restaurados em {settings.db_path}: {counts}")
        if args.sessions:
            repo.clear_sessions()
            removed = clear_adk_sessions()
            print(f"[restore] Sessões apagadas ({removed} linhas removidas do banco de sessões).")
        else:
            print("[restore] Sessões preservadas (use `make reset` para apagá-las também).")
    except (RepositoryError, RuntimeError, sqlite3.Error, OSError) as exc:
        print(f"[restore] ERRO: {exc}", file=sys.stderr)
        print(
            "[restore] Dica: confira AURORA_DB_PATH, AURORA_DADOS_DIR e a permissão de escrita em ./var.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
