"""Fixtures for unit tests: isolated databases and an API wired to the fake model."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from aurora import services
from aurora.config import PROJECT_ROOT, Settings
from aurora.db.repository import Repository
from aurora.db.seed import seed

DADOS = PROJECT_ROOT / "dados"


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    db = tmp_path / "aurora.db"
    monkeypatch.setenv("AURORA_DB_PATH", str(db))
    monkeypatch.setenv("AURORA_SESSIONS_DB_URL", f"sqlite+aiosqlite:///{tmp_path / 'sessions.db'}")
    monkeypatch.setenv("AURORA_DADOS_DIR", str(DADOS))
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-for-tests")
    from aurora.config import get_settings

    get_settings.cache_clear()
    services.get_repository.cache_clear()
    return get_settings()


@pytest.fixture
def repo(settings: Settings) -> Repository:
    repository = Repository(settings.db_path)
    seed(repository, settings.dados_dir)
    return repository


def make_runtime(settings: Settings, repository: Repository):
    from fake_llm import fake_models

    from aurora.runtime import AuroraRuntime

    return AuroraRuntime(settings, repository, models=fake_models())


@pytest.fixture
async def client(settings: Settings, repo: Repository):
    from aurora.api.main import create_app

    runtime = make_runtime(settings, repo)
    app = create_app(settings, runtime=runtime)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
