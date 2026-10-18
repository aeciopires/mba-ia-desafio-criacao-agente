"""Regulation index and the guarantee that the root agent never carries the regulation."""

from __future__ import annotations

from aurora.agents import prompts
from aurora.config import PROJECT_ROOT
from aurora.regulamento.index import RegulationIndex, parse_chapters
from aurora.tools.regulamento import buscar_no_regulamento, ler_capitulo

REGULAMENTO = (PROJECT_ROOT / "dados" / "regulamento.md").read_text(encoding="utf-8")


def test_parses_fourteen_chapters():
    chapters = parse_chapters(REGULAMENTO)
    assert [c.numero for c in chapters] == list(range(1, 15))
    assert chapters[3].titulo == "Piscina"


def test_read_chapter_returns_only_that_chapter(settings):
    result = ler_capitulo(4)
    assert result["titulo"] == "Piscina"
    assert "das 9h às 20h" in result["texto"]
    assert "Capítulo V" not in result["texto"]
    assert "Animais de estimação" not in result["texto"]


def test_search_returns_titles_not_text(settings):
    result = buscar_no_regulamento("piscina domingo horário")
    assert result["capitulos"][0]["numero"] == 4
    assert all(set(c) == {"numero", "titulo", "pontos"} for c in result["capitulos"])


def test_root_instruction_has_no_regulation_text():
    index = RegulationIndex(parse_chapters(REGULAMENTO))
    for chapter in index._chapters.values():
        body_lines = [line for line in chapter.texto.splitlines()[1:] if len(line) > 40]
        for line in body_lines:
            assert line[:40] not in prompts.ROOT_INSTRUCTION
    assert "Art." not in prompts.ROOT_INSTRUCTION
