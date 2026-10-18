"""FastAPI application exposing the contract defined in TASK.md."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .. import __version__, metrics
from ..config import Settings, get_settings
from ..db.repository import Repository
from ..db.seed import ensure_initialized
from ..logging_setup import configure_logging
from ..runtime import (
    AuroraRuntime,
    ConfirmationNotExecutedError,
    ConfirmationNotPendingError,
    SessionNotFoundError,
)
from .schemas import (
    CONFIRMACAO_EXEMPLOS,
    MENSAGEM_EXEMPLOS,
    SESSAO_EXEMPLOS,
    CriarSessao,
    Erro,
    Mensagem,
    ReservaPublica,
    RespostaConfirmacao,
    RespostaConversa,
    SessaoCriada,
    VisitantePublico,
)

logger = logging.getLogger("aurora.api")

DESCRIPTION = """
API do assistente virtual do **Residencial Aurora** (Google ADK + Gemini).

Fluxo típico:
1. `POST /sessoes` com o apartamento do morador → `session_id`.
2. `POST /sessoes/{session_id}/mensagens` com o texto do morador.
3. Se `confirmacoes_pendentes` não vier vazia, responda em `POST /sessoes/{session_id}/confirmacoes`.
4. Confira os efeitos nas rotas de **Verificação**, que leem o banco direto, sem o modelo.

Cenários prontos: `docs/cenarios-de-teste.md`.
"""

SESSION_404 = {404: {"model": Erro, "description": "Sessão não encontrada"}}


def _http_error_for_model(exc: Exception) -> HTTPException:
    hint = metrics.explain_model_error(exc)
    return HTTPException(
        status_code=502,
        detail=f"Falha ao executar o assistente ({type(exc).__name__}: {exc}). {hint}",
    )


def create_app(settings: Settings | None = None, runtime: AuroraRuntime | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repo = Repository(settings.db_path)
        try:
            await asyncio.to_thread(ensure_initialized, repo, settings.dados_dir)
        except Exception:
            logger.exception(
                "Startup failed while preparing the database at %s (dados=%s)",
                settings.db_path,
                settings.dados_dir,
            )
            raise
        metrics.register_business_collector(lambda: repo)
        if not settings.google_api_key:
            logger.error(
                "GOOGLE_API_KEY is empty: conversation routes will fail. "
                "Copy .env.example to .env and set your Google AI Studio key."
            )
        app.state.repo = repo
        app.state.runtime = runtime or AuroraRuntime(settings, repo)
        logger.info(
            "Aurora API %s ready on port %s (db=%s)",
            __version__,
            settings.api_port,
            settings.db_path,
        )
        try:
            yield
        finally:
            await app.state.runtime.close()

    docs = settings.enable_docs
    app = FastAPI(
        title="Residencial Aurora API",
        version=__version__,
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
        openapi_tags=[
            {"name": "Sessões", "description": "Conversa com o assistente."},
            {"name": "Verificação", "description": "Leitura direta dos dados, sem o modelo."},
            {"name": "Operação", "description": "Saúde e métricas."},
        ],
    )

    @app.middleware("http")
    async def observe(request: Request, call_next):
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            path = getattr(route, "path", "unmatched")
            metrics.HTTP_LATENCY.labels(path, request.method, str(status)).observe(
                time.perf_counter() - started
            )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Erro interno ({type(exc).__name__}: {exc}). Veja os logs da API."},
        )

    def runtime_of(request: Request) -> AuroraRuntime:
        return request.app.state.runtime

    # ---------------------------------------------------------------- sessions
    @app.post(
        "/sessoes",
        status_code=201,
        response_model=SessaoCriada,
        tags=["Sessões"],
        responses={422: {"description": "Corpo inválido ou apartamento inexistente"}},
    )
    async def criar_sessao(
        request: Request, body: Annotated[CriarSessao, Body(openapi_examples=SESSAO_EXEMPLOS)]
    ):
        apartamento = body.apartamento.strip()
        if not await asyncio.to_thread(request.app.state.repo.apartment_exists, apartamento):
            raise HTTPException(422, detail=f"Apartamento '{apartamento}' não existe.")
        return SessaoCriada(session_id=await runtime_of(request).create_session(apartamento))

    @app.post(
        "/sessoes/{session_id}/mensagens",
        response_model=RespostaConversa,
        tags=["Sessões"],
        responses={**SESSION_404, 502: {"model": Erro, "description": "Falha no modelo"}},
    )
    async def enviar_mensagem(
        request: Request,
        session_id: str,
        body: Annotated[Mensagem, Body(openapi_examples=MENSAGEM_EXEMPLOS)],
    ):
        try:
            result = await runtime_of(request).send_message(session_id, body.texto)
        except SessionNotFoundError:
            raise HTTPException(404, detail="Sessão não encontrada") from None
        except Exception as exc:
            logger.exception("Agent run failed for session %s", session_id)
            raise _http_error_for_model(exc) from exc
        return RespostaConversa(**result.__dict__)

    @app.post(
        "/sessoes/{session_id}/confirmacoes",
        response_model=RespostaConversa,
        tags=["Sessões"],
        responses={
            **SESSION_404,
            409: {
                "model": Erro,
                "description": "Não existe confirmação pendente com esse id nesta sessão",
            },
            502: {"model": Erro, "description": "Falha no modelo"},
        },
    )
    async def responder_confirmacao(
        request: Request,
        session_id: str,
        body: Annotated[RespostaConfirmacao, Body(openapi_examples=CONFIRMACAO_EXEMPLOS)],
    ):
        try:
            result = await runtime_of(request).answer_confirmation(
                session_id, body.id, body.confirmado
            )
        except SessionNotFoundError:
            raise HTTPException(404, detail="Sessão não encontrada") from None
        except ConfirmationNotPendingError:
            logger.info("409 for confirmation %r in session %s", body.id, session_id)
            raise HTTPException(
                409, detail="Não existe confirmação pendente com esse id nesta sessão"
            ) from None
        except ConfirmationNotExecutedError:
            raise HTTPException(
                500,
                detail="A confirmação foi registrada, mas a ação não executou. Veja os logs da API.",
            ) from None
        except Exception as exc:
            logger.exception("Confirmation run failed for session %s", session_id)
            raise _http_error_for_model(exc) from exc
        return RespostaConversa(**result.__dict__)

    @app.get("/sessoes/{session_id}/eventos", tags=["Sessões"], responses=SESSION_404)
    async def listar_eventos(request: Request, session_id: str) -> list[dict]:
        try:
            return await runtime_of(request).get_events(session_id)
        except SessionNotFoundError:
            raise HTTPException(404, detail="Sessão não encontrada") from None

    # ------------------------------------------------------------ verification
    @app.get(
        "/apartamentos/{numero}/reservas", response_model=list[ReservaPublica], tags=["Verificação"]
    )
    async def reservas_do_apartamento(request: Request, numero: str):
        reservas = await asyncio.to_thread(request.app.state.repo.list_reservations, numero)
        return [ReservaPublica(codigo=r.codigo, area=r.area, data=r.data) for r in reservas]

    @app.get(
        "/apartamentos/{numero}/visitantes",
        response_model=list[VisitantePublico],
        tags=["Verificação"],
    )
    async def visitantes_do_apartamento(request: Request, numero: str):
        return await asyncio.to_thread(request.app.state.repo.list_visitors, numero)

    # -------------------------------------------------------------- operations
    @app.get("/health", tags=["Operação"])
    async def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/metrics", tags=["Operação"], response_class=PlainTextResponse)
    async def prometheus_metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app
