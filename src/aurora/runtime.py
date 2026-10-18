"""ADK runtime: App, Runner and the persisted session service."""

from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from contextvars import ContextVar
from dataclasses import dataclass, field

from google.adk.apps.app import App, ResumabilityConfig
from google.adk.events.event import Event
from google.adk.models.base_llm import BaseLlm
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.adk.sessions.session import Session
from google.genai import types
from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import create_async_engine

from . import confirmations, metrics
from .agents import ROOT_AGENT_NAME, build_root_agent
from .config import Settings
from .db.repository import Repository
from .tools.context import APARTMENT_STATE_KEY

logger = logging.getLogger(__name__)

APP_NAME = "aurora"
FAILED_TURN_NOTE = (
    "(A mensagem anterior não foi processada por uma falha temporária; nada foi executado. "
    "Se ainda for necessário, o morador vai repeti-la.)"
)


class SessionNotFoundError(LookupError):
    """The session id does not exist."""


class ConfirmationNotPendingError(LookupError):
    """The confirmation id is not pending in this session."""


class ConfirmationNotExecutedError(RuntimeError):
    """The confirmation was stored but the tool did not run (routing problem)."""


@dataclass
class TurnResult:
    resposta: str
    confirmacoes_pendentes: list[dict] = field(default_factory=list)


_NEW_TEXT_TURN: ContextVar[bool] = ContextVar("aurora_new_text_turn", default=False)


class AuroraRunner(Runner):
    """Runner whose routing is decided in code.

    - A new text message always starts at the root agent, which triages it. A specialist
      that handled the previous turn cannot keep an unrelated request (for example a
      regulation question) and answer it without the right tools.
    - A confirmation answer (function response) keeps ADK's routing: with the resumable
      App it resumes the invocation of the agent that requested the confirmation.
    """

    async def run_async(self, *args, **kwargs):  # type: ignore[override]
        message = kwargs.get("new_message")
        is_text = bool(
            message and message.parts and not any(part.function_response for part in message.parts)
        )
        token = _NEW_TEXT_TURN.set(is_text)
        try:
            async for event in super().run_async(*args, **kwargs):
                yield event
        finally:
            _NEW_TEXT_TURN.reset(token)

    def _find_agent_to_run(self, session: Session, root_agent):  # type: ignore[override]
        if _NEW_TEXT_TURN.get():
            return root_agent
        return super()._find_agent_to_run(session, root_agent)


def _make_session_engine(url: str):
    engine = create_async_engine(
        url, connect_args={"timeout": 30} if url.startswith("sqlite") else {}
    )
    if url.startswith("sqlite"):

        @sa_event.listens_for(engine.sync_engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - driver hook
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    return engine


def _response_text(events: list[Event]) -> str:
    texts = []
    for event in events:
        if event.author == "user" or not event.content or not event.content.parts:
            continue
        if event.partial:
            continue
        for part in event.content.parts:
            if part.text and not part.thought:
                texts.append(part.text.strip())
    return "\n".join(t for t in texts if t)


class AuroraRuntime:
    """Owns the Runner and serializes turns per session."""

    def __init__(
        self,
        settings: Settings,
        repo: Repository,
        models: dict[str, str | BaseLlm] | None = None,
    ) -> None:
        self.settings = settings
        self.repo = repo
        if settings.google_api_key:
            os.environ.setdefault("GOOGLE_API_KEY", settings.google_api_key)
        url = settings.resolved_sessions_db_url
        if (db_file := settings.sessions_db_file) is not None:
            db_file.parent.mkdir(parents=True, exist_ok=True)
        self.session_service = DatabaseSessionService(db_engine=_make_session_engine(url))
        self.app = App(
            name=APP_NAME,
            root_agent=build_root_agent(models or settings.agent_models),
            plugins=[metrics.MetricsPlugin()],
            # Resumable: a confirmation answer is routed to the agent that authored the
            # adk_request_confirmation call, even if other turns happened in between.
            resumability_config=ResumabilityConfig(is_resumable=True),
        )
        self.runner = AuroraRunner(app=self.app, session_service=self.session_service)
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        logger.info(
            "ADK runtime ready: models=%s sessions=%s",
            models or settings.agent_models,
            url,
        )

    async def close(self) -> None:
        await self.runner.close()

    # ---------------------------------------------------------------- sessions
    async def create_session(self, apartamento: str) -> str:
        session = await self.session_service.create_session(
            app_name=APP_NAME,
            user_id=apartamento,
            state={APARTMENT_STATE_KEY: apartamento},
        )
        await asyncio.to_thread(self.repo.register_session, session.id, apartamento)
        logger.info("Session %s created for apartment %s", session.id, apartamento)
        return session.id

    async def _get_session(self, session_id: str) -> Session:
        apartamento = await asyncio.to_thread(self.repo.get_session_apartment, session_id)
        if apartamento is None:
            raise SessionNotFoundError(session_id)
        session = await self.session_service.get_session(
            app_name=APP_NAME, user_id=apartamento, session_id=session_id
        )
        if session is None:
            logger.error(
                "Session %s is registered for apartment %s but missing in the session database; "
                "was the session database deleted without `make reset`?",
                session_id,
                apartamento,
            )
            raise SessionNotFoundError(session_id)
        return session

    async def get_events(self, session_id: str) -> list[dict]:
        session = await self._get_session(session_id)
        return [e.model_dump(mode="json", by_alias=True, exclude_none=True) for e in session.events]

    # ------------------------------------------------------------------- turns
    async def _run(self, session: Session, message: types.Content) -> list[Event]:
        produced = []
        try:
            async for event in self.runner.run_async(
                user_id=session.user_id, session_id=session.id, new_message=message
            ):
                produced.append(event)
        except Exception:
            await self._mark_failed_turn(session.id, produced)
            raise
        return produced

    async def _mark_failed_turn(self, session_id: str, produced: list[Event]) -> None:
        """Record that the last message was not processed, so the model does not act on it later."""
        try:
            session = await self._get_session(session_id)
            invocation_id = produced[-1].invocation_id if produced else Event.new_id()
            await self.session_service.append_event(
                session,
                Event(
                    invocation_id=invocation_id,
                    author=ROOT_AGENT_NAME,
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text=FAILED_TURN_NOTE)],
                    ),
                ),
            )
        except Exception:  # noqa: BLE001 - never hide the original error
            logger.exception("Could not record the failed-turn note in session %s", session_id)

    async def _finish(self, session_id: str, produced: list[Event]) -> TurnResult:
        session = await self._get_session(session_id)
        pending = confirmations.pending_confirmations(session.events)
        metrics.CONFIRMACOES_PENDENTES.set(len(pending))
        return TurnResult(resposta=_response_text(produced), confirmacoes_pendentes=pending)

    async def send_message(self, session_id: str, texto: str) -> TurnResult:
        async with self._locks[session_id]:
            session = await self._get_session(session_id)
            message = types.Content(role="user", parts=[types.Part(text=texto)])
            produced = await self._run(session, message)
            return await self._finish(session_id, produced)

    async def answer_confirmation(
        self, session_id: str, confirmation_id: str, confirmado: bool
    ) -> TurnResult:
        async with self._locks[session_id]:
            session = await self._get_session(session_id)
            pending_ids = {p["id"] for p in confirmations.pending_confirmations(session.events)}
            if confirmation_id not in pending_ids:
                raise ConfirmationNotPendingError(confirmation_id)
            original_id = confirmations.original_call_id(session.events, confirmation_id)
            before = len(session.events)
            message = types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=confirmations.REQUEST_CONFIRMATION,
                            id=confirmation_id,
                            response={"confirmed": confirmado},
                        )
                    )
                ],
            )
            produced = await self._run(session, message)
            result = await self._finish(session_id, produced)
            refreshed = await self._get_session(session_id)
            if original_id and not confirmations.tool_ran_after(
                refreshed.events, original_id, before
            ):
                logger.error(
                    "Confirmation %s (tool call %s) was stored but the tool did not run. "
                    "The Runner routed the answer to an agent that does not own the call; "
                    "check disallow_transfer_* flags and the App resumability config.",
                    confirmation_id,
                    original_id,
                )
                raise ConfirmationNotExecutedError(confirmation_id)
            return result
