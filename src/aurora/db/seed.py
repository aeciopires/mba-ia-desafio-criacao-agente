"""Loads the read-only initial data from ``dados/*.json`` into the database."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .repository import Repository

logger = logging.getLogger(__name__)

REQUIRED_FILES = ("apartamentos.json", "areas.json", "reservas.json", "visitantes.json")


def _load_json(dados_dir: Path, name: str) -> list[dict]:
    path = dados_dir / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Arquivo de dados ausente: '{path}'. Confira AURORA_DADOS_DIR "
            "(no Docker, o volume ./dados precisa estar montado em /app/dados)."
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON inválido em '{path}': {exc}") from exc


def seed(repo: Repository, dados_dir: Path) -> dict[str, int]:
    """Reset apartments, areas, reservations and visitors to the initial files."""
    data = {name: _load_json(dados_dir, name) for name in REQUIRED_FILES}
    repo.init_schema()
    repo.load_initial_data(
        apartamentos=data["apartamentos.json"],
        areas=data["areas.json"],
        reservas=data["reservas.json"],
        visitantes=data["visitantes.json"],
    )
    counts = {name.removesuffix(".json"): len(rows) for name, rows in data.items()}
    logger.info("Initial data loaded from %s: %s", dados_dir, counts)
    return counts


def ensure_initialized(repo: Repository, dados_dir: Path) -> None:
    """Create the schema and seed it on first start (empty database)."""
    repo.init_schema()
    if not repo.is_seeded():
        logger.info("Empty database at %s, loading initial data", repo.db_path)
        seed(repo, dados_dir)
