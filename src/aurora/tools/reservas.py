"""Reservation tools used by the reservations specialist."""

from __future__ import annotations

import asyncio
import logging

from google.adk.tools.tool_context import ToolContext

from .. import metrics
from ..db.repository import InvalidInputError, validate_date
from ..services import get_repository
from .context import get_session_apartment

logger = logging.getLogger(__name__)


def _brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _invalid(exc: Exception) -> dict:
    return {"status": "erro", "mensagem": str(exc)}


async def listar_areas() -> dict:
    """Lists the common areas that can be reserved, with their fee.

    Returns:
        The areas with id, name, fee in BRL and whether a reservation generates a charge.
    """
    areas = await asyncio.to_thread(get_repository().list_areas)
    return {
        "status": "ok",
        "areas": [
            {"id": a.id, "nome": a.nome, "taxa": a.taxa, "gera_cobranca": a.gera_cobranca}
            for a in areas
        ],
    }


async def verificar_disponibilidade(area: str, data: str) -> dict:
    """Checks whether a common area is free on a date.

    Only says free or taken; it never reveals who holds an existing reservation.

    Args:
        area: Area id (use listar_areas to discover ids, e.g. "salao-de-festas").
        data: Date in YYYY-MM-DD format.
    """
    repo = get_repository()
    try:
        data = validate_date(data)
        area_obj = await asyncio.to_thread(repo.get_area, area)
    except InvalidInputError as exc:
        return _invalid(exc)
    livre = await asyncio.to_thread(repo.is_date_free, area_obj.id, data)
    return {"status": "ok", "area": area_obj.id, "data": data, "disponivel": livre}


async def listar_minhas_reservas(tool_context: ToolContext) -> dict:
    """Lists the active reservations of the apartment that owns this session."""
    apartamento = get_session_apartment(tool_context)
    reservas = await asyncio.to_thread(get_repository().list_reservations, apartamento)
    return {
        "status": "ok",
        "reservas": [{"codigo": r.codigo, "area": r.area, "data": r.data} for r in reservas],
    }


async def reservar_area(area: str, data: str, tool_context: ToolContext) -> dict:
    """Reserves a common area on a date for the apartment that owns this session.

    Areas with a fee generate a charge, so the system holds the reservation until the
    resident approves it through the confirmation route. Never claim the reservation
    was made unless this tool returns status "reservado".

    Args:
        area: Area id (e.g. "salao-de-festas", "churrasqueira", "quadra").
        data: Date in YYYY-MM-DD format.
    """
    apartamento = get_session_apartment(tool_context)
    repo = get_repository()
    try:
        data = validate_date(data)
        area_obj = await asyncio.to_thread(repo.get_area, area)
    except InvalidInputError as exc:
        return _invalid(exc)

    confirmation = tool_context.tool_confirmation
    if confirmation is None:
        # Early, friendly answer only. The real exclusivity check happens on insert.
        if not await asyncio.to_thread(repo.is_date_free, area_obj.id, data):
            metrics.CONFLITOS.labels(area_obj.id).inc()
            return {
                "status": "indisponivel",
                "mensagem": f"{area_obj.nome} já está reservado(a) em {data}. Escolha outra data.",
            }
        if area_obj.gera_cobranca:
            # Guarantee 1: the decision to ask for confirmation is made here, in code.
            tool_context.request_confirmation(
                hint=(
                    f"Reservar {area_obj.nome} em {data} gera cobrança de {_brl(area_obj.taxa)} "
                    f"para o apartamento {apartamento}."
                ),
                payload={"area": area_obj.id, "data": data, "taxa": area_obj.taxa},
            )
            return {
                "status": "aguardando_confirmacao",
                "mensagem": (
                    "A reserva gera cobrança e só será feita depois que o morador aprovar "
                    "a confirmação pendente no aplicativo."
                ),
            }
    elif not confirmation.confirmed:
        metrics.CONFIRMACOES.labels("reservar_area", "negada").inc()
        return {
            "status": "cancelado",
            "mensagem": "O morador recusou a cobrança; nada foi reservado.",
        }
    else:
        metrics.CONFIRMACOES.labels("reservar_area", "aprovada").inc()

    result = await asyncio.to_thread(repo.create_reservation, apartamento, area_obj.id, data)
    if not result.created:
        metrics.CONFLITOS.labels(area_obj.id).inc()
        return {
            "status": "indisponivel",
            "mensagem": f"{area_obj.nome} acabou de ser reservado(a) em {data}. Escolha outra data.",
        }
    metrics.RESERVAS_CRIADAS.labels(apartamento, area_obj.id).inc()
    if area_obj.gera_cobranca:
        metrics.COBRANCAS.labels(area_obj.id).inc()
        metrics.COBRANCAS_VALOR.labels(area_obj.id).inc(area_obj.taxa)
    logger.info(
        "Reservation %s created: apt=%s area=%s data=%s",
        result.reserva.codigo,
        apartamento,
        area_obj.id,
        data,
    )
    return {
        "status": "reservado",
        "codigo": result.reserva.codigo,
        "area": area_obj.id,
        "data": data,
        "cobranca": _brl(area_obj.taxa) if area_obj.gera_cobranca else "sem cobrança",
    }


async def cancelar_reserva(
    tool_context: ToolContext, codigo: str = "", area: str = "", data: str = ""
) -> dict:
    """Cancels an active reservation of the apartment that owns this session.

    Inform the reservation code, or the area and the date. Only reservations of this
    session's apartment can be found; no confirmation is needed.

    Args:
        codigo: Reservation code (e.g. "RSV-1377"), optional.
        area: Area id, optional when the code is given.
        data: Date in YYYY-MM-DD format, optional when the code is given.
    """
    apartamento = get_session_apartment(tool_context)
    repo = get_repository()
    try:
        if data:
            data = validate_date(data)
        area_id = (await asyncio.to_thread(repo.get_area, area)).id if area else ""
        reserva = await asyncio.to_thread(
            repo.cancel_reservation, apartamento, codigo, area_id, data
        )
    except InvalidInputError as exc:
        return _invalid(exc)
    if reserva is None:
        metrics.OUTRO_APARTAMENTO.inc()
        # Same answer whether the reservation does not exist or belongs to someone else.
        return {
            "status": "nao_encontrada",
            "mensagem": "Não há reserva ativa do seu apartamento com esses dados.",
        }
    metrics.RESERVAS_CANCELADAS.labels(apartamento, reserva.area).inc()
    logger.info("Reservation %s cancelled by apt=%s", reserva.codigo, apartamento)
    return {
        "status": "cancelada",
        "codigo": reserva.codigo,
        "area": reserva.area,
        "data": reserva.data,
    }
