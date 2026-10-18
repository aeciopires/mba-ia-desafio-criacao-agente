"""Prometheus metrics: ADK/LLM activity and business rules."""

from __future__ import annotations

import logging
import time
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from prometheus_client import Counter, Gauge, Histogram, Info
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import REGISTRY, Collector

from . import __version__

logger = logging.getLogger(__name__)

BUILD_INFO = Info("aurora_build", "Build information")
BUILD_INFO.info({"version": __version__})

# ----------------------------------------------------------------- ADK / LLM
LLM_CALLS = Counter("aurora_llm_calls_total", "Model calls", ["agent", "model"])
LLM_ERRORS = Counter("aurora_llm_errors_total", "Model call errors", ["agent", "error"])
LLM_LATENCY = Histogram(
    "aurora_llm_latency_seconds",
    "Model call latency",
    ["agent"],
    buckets=(0.25, 0.5, 1, 2, 3, 5, 8, 13, 21, 34, 60),
)
LLM_TOKENS = Counter("aurora_llm_tokens_total", "Tokens used", ["agent", "type"])
TOOL_CALLS = Counter("aurora_tool_calls_total", "Tool calls", ["tool", "status"])
AGENT_TRANSFERS = Counter("aurora_agent_transfers_total", "Agent transfers", ["to"])
HTTP_LATENCY = Histogram(
    "aurora_http_request_duration_seconds",
    "HTTP request latency",
    ["route", "method", "status"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 40, 80),
)

# ------------------------------------------------------------------ business
RESERVAS_CRIADAS = Counter(
    "aurora_reservas_criadas_total", "Reservations created", ["apartamento", "area"]
)
RESERVAS_CANCELADAS = Counter(
    "aurora_reservas_canceladas_total", "Reservations cancelled", ["apartamento", "area"]
)
COBRANCAS = Counter("aurora_cobrancas_total", "Charges generated", ["area"])
COBRANCAS_VALOR = Counter("aurora_cobrancas_valor_reais_total", "Charged amount (BRL)", ["area"])
VISITANTES = Counter("aurora_visitantes_autorizados_total", "Visitors authorized", ["apartamento"])
CONFIRMACOES = Counter("aurora_confirmacoes_total", "Confirmation answers", ["acao", "resultado"])
CONFIRMACOES_PENDENTES = Gauge(
    "aurora_confirmacoes_pendentes", "Pending confirmations in the last answered session"
)
CONFLITOS = Counter(
    "aurora_conflitos_reserva_total", "Reservations refused because the date was taken", ["area"]
)
OUTRO_APARTAMENTO = Counter(
    "aurora_tentativas_outro_apartamento_total",
    "Requests about reservations that do not belong to the session apartment",
)


class BusinessCollector(Collector):
    """Reads aggregates from the database on every scrape."""

    def __init__(self, repo_factory) -> None:
        self._repo_factory = repo_factory

    def collect(self):
        try:
            snap = self._repo_factory().business_snapshot()
        except Exception:  # noqa: BLE001 - a scrape must never crash the API
            logger.exception("Could not collect business metrics from the database")
            return
        yield GaugeMetricFamily("aurora_apartamentos", "Apartments", value=snap["apartamentos"])
        yield GaugeMetricFamily("aurora_sessoes", "Sessions created", value=snap["sessoes"])
        for name, key, label in (
            ("aurora_reservas_ativas_por_area", "reservas_por_area", "area"),
            ("aurora_reservas_ativas_por_data", "reservas_por_data", "data"),
            ("aurora_reservas_ativas_por_apartamento", "reservas_por_apartamento", "apartamento"),
            ("aurora_visitantes_por_apartamento", "visitantes_por_apartamento", "apartamento"),
        ):
            family = GaugeMetricFamily(name, name.replace("_", " "), labels=[label])
            for value, count in snap[key].items():
                family.add_metric([value], count)
            yield family


_collector_registered = False


def register_business_collector(repo_factory) -> None:
    global _collector_registered
    if not _collector_registered:
        REGISTRY.register(BusinessCollector(repo_factory))
        _collector_registered = True


class MetricsPlugin(BasePlugin):
    """ADK plugin: model/tool metrics plus explicit error logs for root-cause analysis."""

    def __init__(self) -> None:
        super().__init__(name="aurora_metrics")
        self._started: dict[str, float] = {}

    @staticmethod
    def _key(callback_context: CallbackContext) -> str:
        return f"{callback_context.invocation_id}:{callback_context.agent_name}"

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        self._started[self._key(callback_context)] = time.perf_counter()
        LLM_CALLS.labels(callback_context.agent_name, llm_request.model or "?").inc()
        return None

    async def after_model_callback(
        self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> LlmResponse | None:
        started = self._started.pop(self._key(callback_context), None)
        if started is not None:
            LLM_LATENCY.labels(callback_context.agent_name).observe(time.perf_counter() - started)
        usage = llm_response.usage_metadata
        if usage:
            agent = callback_context.agent_name
            LLM_TOKENS.labels(agent, "prompt").inc(usage.prompt_token_count or 0)
            LLM_TOKENS.labels(agent, "output").inc(usage.candidates_token_count or 0)
        if llm_response.error_code:
            LLM_ERRORS.labels(callback_context.agent_name, str(llm_response.error_code)).inc()
            logger.error(
                "Model returned an error for agent=%s: code=%s message=%s",
                callback_context.agent_name,
                llm_response.error_code,
                llm_response.error_message,
            )
        return None

    async def on_model_error_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest, error: Exception
    ) -> LlmResponse | None:
        self._started.pop(self._key(callback_context), None)
        LLM_ERRORS.labels(callback_context.agent_name, type(error).__name__).inc()
        logger.error(
            "Model call failed for agent=%s model=%s: %s: %s. %s",
            callback_context.agent_name,
            llm_request.model,
            type(error).__name__,
            error,
            explain_model_error(error),
        )
        return None

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict,
    ) -> dict | None:
        status = "ok"
        if isinstance(result, dict):
            status = str(result.get("status", "ok"))
        TOOL_CALLS.labels(tool.name, status).inc()
        if tool.name == "transfer_to_agent":
            AGENT_TRANSFERS.labels(str(tool_args.get("agent_name", "?"))).inc()
        return None

    async def on_tool_error_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        error: Exception,
    ) -> dict | None:
        TOOL_CALLS.labels(tool.name, "error").inc()
        logger.error(
            "Tool %s failed (agent=%s, args=%s): %s: %s",
            tool.name,
            tool_context.agent_name,
            tool_args,
            type(error).__name__,
            error,
            exc_info=error,
        )
        # Give the model a safe, structured error instead of aborting the turn.
        return {
            "status": "erro",
            "mensagem": "Falha interna ao executar a operação. Nada foi alterado; tente novamente.",
        }


def explain_model_error(error: Exception) -> str:
    """Map common Gemini failures to an actionable hint."""
    text = f"{type(error).__name__} {error}".lower()
    if "api key" in text or "api_key" in text or "permission" in text or "403" in text:
        return "Hint: check GOOGLE_API_KEY in .env (it must be a Google AI Studio key)."
    if "429" in text or "resource_exhausted" in text or "quota" in text:
        return "Hint: Gemini rate limit/quota reached; wait a moment or change AURORA_MODEL_* to another model."
    if "404" in text or "not found" in text:
        return "Hint: the model name in AURORA_MODEL_ROOT/AURORA_MODEL_SPECIALIST may not exist for this key."
    if "timeout" in text or "connect" in text:
        return "Hint: network problem reaching generativelanguage.googleapis.com."
    return "Hint: see the stack trace above."
