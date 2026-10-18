"""Process-wide service accessors (repository, regulation index)."""

from __future__ import annotations

from functools import lru_cache

from .config import get_settings
from .db.repository import Repository
from .regulamento.index import RegulationIndex, get_index


@lru_cache
def get_repository() -> Repository:
    return Repository(get_settings().db_path)


def get_regulation() -> RegulationIndex:
    return get_index(str(get_settings().dados_dir / "regulamento.md"))
