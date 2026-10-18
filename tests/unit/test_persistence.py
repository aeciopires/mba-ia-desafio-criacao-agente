"""Guarantee 3: sessions, pending confirmations and data survive a restart."""

from __future__ import annotations

import httpx

from aurora.api.main import create_app
from conftest import make_runtime


async def _client_for(settings, repo):
    app = create_app(settings, runtime=make_runtime(settings, repo))
    return app


async def test_session_and_pending_confirmation_survive_restart(settings, repo):
    app = await _client_for(settings, repo)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c,
    ):
        sid = (await c.post("/sessoes", json={"apartamento": "101"})).json()["session_id"]
        body = (
            await c.post(
                f"/sessoes/{sid}/mensagens",
                json={"texto": "Reserve a churrasqueira para 2030-06-01."},
            )
        ).json()
        conf_id = body["confirmacoes_pendentes"][0]["id"]
        before = len((await c.get(f"/sessoes/{sid}/eventos")).json())

    # "Restart": brand-new runtime, runner and session service over the same files.
    app = await _client_for(settings, repo)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c,
    ):
        events = (await c.get(f"/sessoes/{sid}/eventos")).json()
        assert len(events) == before
        r = await c.post(f"/sessoes/{sid}/confirmacoes", json={"id": conf_id, "confirmado": True})
        assert r.status_code == 200, r.text
        reservas = (await c.get("/apartamentos/101/reservas")).json()
        assert sum(1 for x in reservas if x["area"] == "churrasqueira") == 1
        r = await c.post(
            f"/sessoes/{sid}/mensagens", json={"texto": "Quais são as minhas reservas agora?"}
        )
        assert r.status_code == 200
        assert len((await c.get(f"/sessoes/{sid}/eventos")).json()) > before
