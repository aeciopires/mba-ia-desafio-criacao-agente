"""Regulation tools, used only by the regulation specialist (Guarantee 4).

They return at most one chapter at a time, and they run inside an AgentTool, whose
events live in an isolated in-memory session: the chapter text never reaches the
persisted conversation, only the specialist's final answer does.
"""

from __future__ import annotations

from ..services import get_regulation


def buscar_no_regulamento(termo: str) -> dict:
    """Finds which chapters of the internal regulation talk about a subject.

    Returns chapter numbers and titles only (no text). Use ler_capitulo next.

    Args:
        termo: Subject keywords in Portuguese, e.g. "piscina domingo horário".
    """
    index = get_regulation()
    return {"status": "ok", "capitulos": index.search(termo), "todos_os_titulos": index.titles()}


def ler_capitulo(numero: int) -> dict:
    """Reads the full text of ONE chapter of the internal regulation.

    Args:
        numero: Chapter number (1 to 14), as returned by buscar_no_regulamento.
    """
    chapter = get_regulation().chapter(int(numero))
    if chapter is None:
        return {"status": "erro", "mensagem": f"Capítulo {numero} não existe."}
    return {
        "status": "ok",
        "numero": chapter.numero,
        "titulo": chapter.titulo,
        "texto": chapter.texto,
    }
