"""Data access for the condominium (apartments, areas, reservations, visitors, sessions).

All functions are synchronous and open a short-lived SQLite connection; async callers
use ``asyncio.to_thread``. Writes run inside ``BEGIN IMMEDIATE`` transactions.
"""

from __future__ import annotations

import logging
import re
import secrets
import sqlite3
import string
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_SCHEMA_FILE = Path(__file__).with_name("schema.sql")
_CODE_ALPHABET = string.ascii_uppercase + string.digits
_CODE_LENGTH = 6
_MAX_CODE_ATTEMPTS = 20
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class RepositoryError(Exception):
    """Base error for the repository layer."""


class InvalidInputError(RepositoryError):
    """Raised when an argument is invalid (unknown area, malformed date...)."""


@dataclass(frozen=True)
class Area:
    id: str
    nome: str
    taxa: float

    @property
    def gera_cobranca(self) -> bool:
        """Business rule 2: only areas with a fee greater than zero generate a charge."""
        return self.taxa > 0


@dataclass(frozen=True)
class Reserva:
    codigo: str
    apartamento: str
    area: str
    data: str


@dataclass(frozen=True)
class ReservaResult:
    """Outcome of a reservation attempt."""

    created: bool
    reserva: Reserva | None = None
    reason: str = ""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def validate_date(value: str) -> str:
    """Validate an ISO date (YYYY-MM-DD) and return it normalized."""
    value = (value or "").strip()
    if not _DATE_RE.match(value):
        raise InvalidInputError(f"Data inválida '{value}': use o formato AAAA-MM-DD.")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise InvalidInputError(f"Data inválida '{value}': {exc}.") from exc
    return value


class Repository:
    """SQLite-backed repository. One instance per database file."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)

    # ------------------------------------------------------------------ infra
    def connect(self) -> sqlite3.Connection:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        except (OSError, sqlite3.Error) as exc:
            raise RepositoryError(
                f"Não foi possível abrir o banco SQLite em '{self.db_path}': {exc}. "
                "Verifique se o diretório existe e tem permissão de escrita "
                "(no Docker, o bind mount ./var precisa pertencer ao seu usuário)."
            ) from exc
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def _read(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self._read() as conn:
            conn.executescript(_SCHEMA_FILE.read_text(encoding="utf-8"))

    def is_seeded(self) -> bool:
        with self._read() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM apartamentos").fetchone()
            return bool(row["n"])

    # ----------------------------------------------------------------- seeding
    def load_initial_data(
        self,
        apartamentos: list[dict],
        areas: list[dict],
        reservas: list[dict],
        visitantes: list[dict],
    ) -> None:
        """Replace apartments, areas, reservations and visitors with the initial state.

        Issued codes (``codigos_emitidos``) are kept so that a code is never reused.
        """
        now = _now()
        with self._write() as conn:
            conn.execute("DELETE FROM reservas")
            conn.execute("DELETE FROM visitantes")
            conn.execute("DELETE FROM areas")
            conn.execute("DELETE FROM apartamentos")
            conn.executemany(
                "INSERT INTO apartamentos (numero, morador) VALUES (?, ?)",
                [(a["numero"], a["morador"]) for a in apartamentos],
            )
            conn.executemany(
                "INSERT INTO areas (id, nome, taxa) VALUES (?, ?, ?)",
                [(a["id"], a["nome"], float(a["taxa"])) for a in areas],
            )
            conn.executemany(
                "INSERT INTO reservas (codigo, apartamento, area, data, status, criada_em) "
                "VALUES (?, ?, ?, ?, 'ativa', ?)",
                [(r["codigo"], r["apartamento"], r["area"], r["data"], now) for r in reservas],
            )
            conn.executemany(
                "INSERT OR IGNORE INTO codigos_emitidos (codigo, emitido_em) VALUES (?, ?)",
                [(r["codigo"], now) for r in reservas],
            )
            conn.executemany(
                "INSERT INTO visitantes (apartamento, nome, data, criado_em) VALUES (?, ?, ?, ?)",
                [(v["apartamento"], v["nome"], v["data"], now) for v in visitantes],
            )

    def clear_sessions(self) -> None:
        with self._write() as conn:
            conn.execute("DELETE FROM sessoes")

    # -------------------------------------------------------------- apartments
    def apartment_exists(self, numero: str) -> bool:
        with self._read() as conn:
            row = conn.execute("SELECT 1 FROM apartamentos WHERE numero = ?", (numero,)).fetchone()
            return row is not None

    def count_apartments(self) -> int:
        with self._read() as conn:
            return conn.execute("SELECT COUNT(*) FROM apartamentos").fetchone()[0]

    # ------------------------------------------------------------------- areas
    def list_areas(self) -> list[Area]:
        with self._read() as conn:
            rows = conn.execute("SELECT id, nome, taxa FROM areas ORDER BY nome").fetchall()
            return [Area(r["id"], r["nome"], r["taxa"]) for r in rows]

    def get_area(self, area_id: str) -> Area:
        area_id = (area_id or "").strip()
        with self._read() as conn:
            row = conn.execute(
                "SELECT id, nome, taxa FROM areas WHERE id = ?", (area_id,)
            ).fetchone()
        if row is None:
            valid = ", ".join(a.id for a in self.list_areas())
            raise InvalidInputError(f"Área desconhecida '{area_id}'. Áreas válidas: {valid}.")
        return Area(row["id"], row["nome"], row["taxa"])

    # ------------------------------------------------------------ reservations
    def is_date_free(self, area_id: str, data: str) -> bool:
        """Only says whether the date is free; never reveals who holds it (Guarantee 2)."""
        with self._read() as conn:
            row = conn.execute(
                "SELECT 1 FROM reservas WHERE area = ? AND data = ? AND status = 'ativa'",
                (area_id, data),
            ).fetchone()
            return row is None

    def list_reservations(self, apartamento: str) -> list[Reserva]:
        with self._read() as conn:
            rows = conn.execute(
                "SELECT codigo, apartamento, area, data FROM reservas "
                "WHERE apartamento = ? AND status = 'ativa' ORDER BY data, area",
                (apartamento,),
            ).fetchall()
            return [Reserva(r["codigo"], r["apartamento"], r["area"], r["data"]) for r in rows]

    def create_reservation(self, apartamento: str, area_id: str, data: str) -> ReservaResult:
        """Insert a reservation. The partial unique index decides the winner atomically."""
        for _ in range(_MAX_CODE_ATTEMPTS):
            codigo = "RSV-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))
            now = _now()
            try:
                with self._write() as conn:
                    conn.execute(
                        "INSERT INTO codigos_emitidos (codigo, emitido_em) VALUES (?, ?)",
                        (codigo, now),
                    )
                    conn.execute(
                        "INSERT INTO reservas (codigo, apartamento, area, data, status, criada_em) "
                        "VALUES (?, ?, ?, ?, 'ativa', ?)",
                        (codigo, apartamento, area_id, data, now),
                    )
            except sqlite3.IntegrityError as exc:
                message = str(exc)
                if "codigos_emitidos" in message or "reservas.codigo" in message:
                    logger.warning("Reservation code collision for %s, retrying", codigo)
                    continue
                if "reservas.area" in message or "reservas.data" in message:
                    logger.info(
                        "Reservation rejected by unique index: area=%s data=%s apartamento=%s",
                        area_id,
                        data,
                        apartamento,
                    )
                    return ReservaResult(created=False, reason="indisponivel")
                raise RepositoryError(f"Falha de integridade ao gravar a reserva: {exc}") from exc
            return ReservaResult(created=True, reserva=Reserva(codigo, apartamento, area_id, data))
        raise RepositoryError(
            f"Não foi possível gerar um código de reserva único após {_MAX_CODE_ATTEMPTS} tentativas."
        )

    def cancel_reservation(
        self, apartamento: str, codigo: str = "", area_id: str = "", data: str = ""
    ) -> Reserva | None:
        """Cancel an ACTIVE reservation that belongs to ``apartamento``. Returns None if not found.

        The ownership filter is part of the SQL, so another apartment's reservation can never
        be matched, whatever code, area or date the model passes.
        """
        clauses = ["apartamento = ?", "status = 'ativa'"]
        params: list[str] = [apartamento]
        if codigo:
            clauses.append("codigo = ?")
            params.append(codigo.strip().upper())
        if area_id:
            clauses.append("area = ?")
            params.append(area_id)
        if data:
            clauses.append("data = ?")
            params.append(data)
        if len(params) == 1:
            raise InvalidInputError("Informe o código da reserva ou a área e a data.")
        with self._write() as conn:
            rows = conn.execute(
                f"SELECT codigo, apartamento, area, data FROM reservas WHERE {' AND '.join(clauses)}",
                params,
            ).fetchall()
            if len(rows) != 1:
                if len(rows) > 1:
                    raise InvalidInputError(
                        "Mais de uma reserva corresponde ao pedido; informe a área e a data."
                    )
                return None
            row = rows[0]
            conn.execute(
                "UPDATE reservas SET status = 'cancelada', cancelada_em = ? WHERE codigo = ?",
                (_now(), row["codigo"]),
            )
            return Reserva(row["codigo"], row["apartamento"], row["area"], row["data"])

    # ----------------------------------------------------------------- visitors
    def list_visitors(self, apartamento: str) -> list[dict]:
        with self._read() as conn:
            rows = conn.execute(
                "SELECT nome, data FROM visitantes WHERE apartamento = ? ORDER BY data, id",
                (apartamento,),
            ).fetchall()
            return [{"nome": r["nome"], "data": r["data"]} for r in rows]

    def authorize_visitor(self, apartamento: str, nome: str, data: str) -> dict:
        nome = " ".join((nome or "").split())
        if not nome:
            raise InvalidInputError("Informe o nome do visitante.")
        with self._write() as conn:
            conn.execute(
                "INSERT INTO visitantes (apartamento, nome, data, criado_em) VALUES (?, ?, ?, ?)",
                (apartamento, nome, data, _now()),
            )
        return {"nome": nome, "data": data}

    # ----------------------------------------------------------------- sessions
    def register_session(self, session_id: str, apartamento: str) -> None:
        with self._write() as conn:
            conn.execute(
                "INSERT INTO sessoes (session_id, apartamento, criada_em) VALUES (?, ?, ?)",
                (session_id, apartamento, _now()),
            )

    def get_session_apartment(self, session_id: str) -> str | None:
        with self._read() as conn:
            row = conn.execute(
                "SELECT apartamento FROM sessoes WHERE session_id = ?", (session_id,)
            ).fetchone()
            return row["apartamento"] if row else None

    def count_sessions(self) -> int:
        with self._read() as conn:
            return conn.execute("SELECT COUNT(*) FROM sessoes").fetchone()[0]

    # ------------------------------------------------------------------ metrics
    def business_snapshot(self) -> dict:
        """Aggregates used by the Prometheus collector (read-only)."""
        with self._read() as conn:
            by_area = conn.execute(
                "SELECT area, COUNT(*) AS n FROM reservas WHERE status = 'ativa' GROUP BY area"
            ).fetchall()
            by_date = conn.execute(
                "SELECT data, COUNT(*) AS n FROM reservas WHERE status = 'ativa' "
                "GROUP BY data ORDER BY n DESC, data LIMIT 30"
            ).fetchall()
            by_apartment = conn.execute(
                "SELECT apartamento, COUNT(*) AS n FROM reservas WHERE status = 'ativa' "
                "GROUP BY apartamento"
            ).fetchall()
            visitors = conn.execute(
                "SELECT apartamento, COUNT(*) AS n FROM visitantes GROUP BY apartamento"
            ).fetchall()
            return {
                "apartamentos": conn.execute("SELECT COUNT(*) FROM apartamentos").fetchone()[0],
                "sessoes": conn.execute("SELECT COUNT(*) FROM sessoes").fetchone()[0],
                "reservas_por_area": {r["area"]: r["n"] for r in by_area},
                "reservas_por_data": {r["data"]: r["n"] for r in by_date},
                "reservas_por_apartamento": {r["apartamento"]: r["n"] for r in by_apartment},
                "visitantes_por_apartamento": {r["apartamento"]: r["n"] for r in visitors},
            }
