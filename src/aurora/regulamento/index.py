"""Chapter index of ``dados/regulamento.md``.

The regulation is never loaded into an agent instruction. The regulation specialist reads
one chapter at a time through tools (Guarantee 4).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_CHAPTER_RE = re.compile(r"^## (Capítulo [IVXLC]+): (.+)$", re.MULTILINE)
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


@dataclass(frozen=True)
class Chapter:
    numero: int
    titulo: str
    texto: str


def _roman_to_int(value: str) -> int:
    total = 0
    for current, nxt in zip(value, value[1:] + " ", strict=False):
        number = _ROMAN[current]
        total += -number if nxt in _ROMAN and _ROMAN[nxt] > number else number
    return total


def _normalize(text: str) -> str:
    stripped = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in stripped if not unicodedata.combining(c))


def parse_chapters(markdown: str) -> list[Chapter]:
    """Split the regulation into chapters (the document title is not part of any chapter)."""
    matches = list(_CHAPTER_RE.finditer(markdown))
    chapters = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        roman = match.group(1).split()[-1]
        chapters.append(
            Chapter(
                numero=_roman_to_int(roman),
                titulo=match.group(2).strip(),
                texto=markdown[match.start() : end].strip(),
            )
        )
    return chapters


class RegulationIndex:
    def __init__(self, chapters: list[Chapter]) -> None:
        if not chapters:
            raise ValueError("O regulamento não tem capítulos no formato '## Capítulo N: Título'.")
        self._chapters = {c.numero: c for c in chapters}

    @classmethod
    def from_file(cls, path: Path) -> RegulationIndex:
        try:
            return cls(parse_chapters(path.read_text(encoding="utf-8")))
        except FileNotFoundError as exc:
            raise RuntimeError(f"Regulamento não encontrado em '{path}'.") from exc

    def titles(self) -> list[dict]:
        return [{"numero": c.numero, "titulo": c.titulo} for c in self._chapters.values()]

    def chapter(self, numero: int) -> Chapter | None:
        return self._chapters.get(numero)

    def search(self, termo: str) -> list[dict]:
        """Rank chapters by how often the (accent-insensitive) words of ``termo`` appear.

        Returns only chapter numbers, titles and hit counts, never chapter text.
        """
        words = [w for w in re.findall(r"\w+", _normalize(termo)) if len(w) > 2]
        ranking = []
        for chapter in self._chapters.values():
            body = _normalize(chapter.texto)
            title = _normalize(chapter.titulo)
            hits = sum(body.count(w) + 5 * title.count(w) for w in words)
            if hits:
                ranking.append({"numero": chapter.numero, "titulo": chapter.titulo, "pontos": hits})
        return sorted(ranking, key=lambda r: r["pontos"], reverse=True)[:3]


@lru_cache
def get_index(path: str) -> RegulationIndex:
    return RegulationIndex.from_file(Path(path))
