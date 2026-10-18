-- Condominium data. Reservations and visitors are never read from model memory:
-- every read and write goes through the tools backed by these tables.

CREATE TABLE IF NOT EXISTS apartamentos (
    numero  TEXT PRIMARY KEY,
    morador TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS areas (
    id   TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    taxa REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS reservas (
    codigo       TEXT PRIMARY KEY,
    apartamento  TEXT NOT NULL,
    area         TEXT NOT NULL REFERENCES areas(id),
    data         TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'ativa' CHECK (status IN ('ativa', 'cancelada')),
    criada_em    TEXT NOT NULL,
    cancelada_em TEXT
);

-- Guarantee 5: at most one ACTIVE reservation per area and date, enforced by the
-- database at the exact moment the row is written (not by a check made before).
CREATE UNIQUE INDEX IF NOT EXISTS ux_reserva_ativa
    ON reservas (area, data) WHERE status = 'ativa';

CREATE INDEX IF NOT EXISTS ix_reservas_apartamento ON reservas (apartamento);

-- Business rule 5: every code ever issued, including cancelled reservations.
-- This table is never truncated, not even by the restore command.
CREATE TABLE IF NOT EXISTS codigos_emitidos (
    codigo     TEXT PRIMARY KEY,
    emitido_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS visitantes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    apartamento TEXT NOT NULL,
    nome        TEXT NOT NULL,
    data        TEXT NOT NULL,
    criado_em   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_visitantes_apartamento ON visitantes (apartamento);

-- Guarantee 2: the owner apartment of each session, fixed at creation time.
CREATE TABLE IF NOT EXISTS sessoes (
    session_id  TEXT PRIMARY KEY,
    apartamento TEXT NOT NULL,
    criada_em   TEXT NOT NULL
);
