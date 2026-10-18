"""Agent tree: one root agent and three specialists.

- ``aurora_concierge`` (root): understands the request and delegates.
- ``reservas_agent`` (sub-agent, reached by transfer): reservations.
- ``visitantes_agent`` (sub-agent, reached by transfer): visitor authorizations.
- ``regulamento_agent`` (AgentTool called by the root): regulation questions.

The transactional specialists keep ``disallow_transfer_to_parent=False``: the Runner only
routes a confirmation answer back to the agent that requested it when that agent is
transferable or the app is resumable (validated in the Phase 1 spike; with
``disallow_transfer_to_parent=True`` the approval was silently ignored).
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from ..tools.regulamento import buscar_no_regulamento, ler_capitulo
from ..tools.reservas import (
    cancelar_reserva,
    listar_areas,
    listar_minhas_reservas,
    reservar_area,
    verificar_disponibilidade,
)
from ..tools.visitantes import autorizar_visitante, listar_meus_visitantes
from .prompts import (
    REGULAMENTO_INSTRUCTION,
    RESERVAS_INSTRUCTION,
    ROOT_INSTRUCTION,
    VISITANTES_INSTRUCTION,
)

ROOT_AGENT_NAME = "aurora_concierge"

_GEN_CONFIG = types.GenerateContentConfig(temperature=0.1)

# Free-tier Gemini keys have low per-minute quotas; retry 429/5xx with exponential
# backoff (2s, 4s, 8s, 16s, 32s) so a burst waits instead of failing the request.
_RETRY = types.HttpRetryOptions(
    attempts=6, initial_delay=2, max_delay=40, exp_base=2, http_status_codes=[429, 500, 503, 504]
)


def _model(model: str | BaseLlm) -> BaseLlm:
    return Gemini(model=model, retry_options=_RETRY) if isinstance(model, str) else model


def build_root_agent(models: dict[str, str | BaseLlm]) -> LlmAgent:
    """Build the agent tree. ``models`` maps root/reservas/visitantes/regulamento to a model."""
    m = {key: _model(value) for key, value in models.items()}
    reservas = LlmAgent(
        name="reservas_agent",
        model=m["reservas"],
        description="Checks availability, lists, books and cancels common-area reservations.",
        instruction=RESERVAS_INSTRUCTION,
        tools=[
            listar_areas,
            verificar_disponibilidade,
            listar_minhas_reservas,
            reservar_area,
            cancelar_reserva,
        ],
        generate_content_config=_GEN_CONFIG,
        disallow_transfer_to_parent=False,
    )
    visitantes = LlmAgent(
        name="visitantes_agent",
        model=m["visitantes"],
        description="Lists visitors and authorizes building access for visitors.",
        instruction=VISITANTES_INSTRUCTION,
        tools=[listar_meus_visitantes, autorizar_visitante],
        generate_content_config=_GEN_CONFIG,
        disallow_transfer_to_parent=False,
    )
    regulamento = LlmAgent(
        name="regulamento_agent",
        model=m["regulamento"],
        description=(
            "Answers questions about the condominium internal regulation. "
            "Pass the resident's question as the request."
        ),
        instruction=REGULAMENTO_INSTRUCTION,
        tools=[buscar_no_regulamento, ler_capitulo],
        generate_content_config=_GEN_CONFIG,
    )
    return LlmAgent(
        name=ROOT_AGENT_NAME,
        model=m["root"],
        description="Residencial Aurora virtual assistant.",
        instruction=ROOT_INSTRUCTION,
        tools=[AgentTool(agent=regulamento)],
        sub_agents=[reservas, visitantes],
        generate_content_config=_GEN_CONFIG,
    )
