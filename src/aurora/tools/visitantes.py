"""Visitor tools used by the visitors specialist."""

from __future__ import annotations

import asyncio
import logging

from google.adk.tools.tool_context import ToolContext

from .. import metrics
from ..db.repository import InvalidInputError, validate_date
from ..services import get_repository
from .context import get_session_apartment

logger = logging.getLogger(__name__)


async def listar_meus_visitantes(tool_context: ToolContext) -> dict:
    """Lists the visitor authorizations of the apartment that owns this session."""
    apartamento = get_session_apartment(tool_context)
    visitantes = await asyncio.to_thread(get_repository().list_visitors, apartamento)
    return {"status": "ok", "visitantes": visitantes}


async def autorizar_visitante(nome: str, data: str, tool_context: ToolContext) -> dict:
    """Authorizes a visitor to enter the building on a date.

    Releasing building access always requires the resident's approval through the
    confirmation route; a chat message saying "I confirm" is not an approval. Never claim
    the visitor was authorized unless this tool returns status "autorizado".

    Args:
        nome: Visitor's full name.
        data: Visit date in YYYY-MM-DD format.
    """
    apartamento = get_session_apartment(tool_context)
    try:
        data = validate_date(data)
        nome = " ".join((nome or "").split())
        if not nome:
            raise InvalidInputError("Informe o nome completo do visitante.")
    except InvalidInputError as exc:
        return {"status": "erro", "mensagem": str(exc)}

    confirmation = tool_context.tool_confirmation
    if confirmation is None:
        # Guarantee 1: building access is always held until the system confirmation.
        tool_context.request_confirmation(
            hint=f"Liberar a entrada de {nome} em {data} para o apartamento {apartamento}.",
            payload={"nome": nome, "data": data},
        )
        return {
            "status": "aguardando_confirmacao",
            "mensagem": (
                "A autorização libera acesso ao prédio e só será registrada depois que o "
                "morador aprovar a confirmação pendente no aplicativo."
            ),
        }
    if not confirmation.confirmed:
        metrics.CONFIRMACOES.labels("autorizar_visitante", "negada").inc()
        return {"status": "cancelado", "mensagem": "O morador recusou; nenhum acesso foi liberado."}

    metrics.CONFIRMACOES.labels("autorizar_visitante", "aprovada").inc()
    try:
        visitante = await asyncio.to_thread(
            get_repository().authorize_visitor, apartamento, nome, data
        )
    except InvalidInputError as exc:
        return {"status": "erro", "mensagem": str(exc)}
    metrics.VISITANTES.labels(apartamento).inc()
    logger.info("Visitor authorized: apt=%s data=%s", apartamento, data)
    return {"status": "autorizado", **visitante}
