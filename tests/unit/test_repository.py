"""Repository: seeding, ownership filters, unique codes and write-time exclusivity."""

from __future__ import annotations

import concurrent.futures

import pytest

from aurora.db.repository import InvalidInputError, Repository, validate_date
from aurora.db.seed import seed


def test_seed_loads_initial_state(repo: Repository):
    assert [r.codigo for r in repo.list_reservations("101")] == ["RSV-1377"]
    assert repo.list_visitors("302") == [{"nome": "Marina Duarte", "data": "2030-03-16"}]
    assert repo.count_apartments() == 6


def test_area_fee_decides_charge(repo: Repository):
    assert repo.get_area("salao-de-festas").gera_cobranca
    assert repo.get_area("churrasqueira").gera_cobranca
    assert not repo.get_area("quadra").gera_cobranca


def test_unknown_area_and_bad_date_are_rejected(repo: Repository):
    with pytest.raises(InvalidInputError, match="Áreas válidas"):
        repo.get_area("piscina")
    with pytest.raises(InvalidInputError):
        validate_date("20/04/2030")
    with pytest.raises(InvalidInputError):
        validate_date("2030-02-30")


def test_date_availability_never_reveals_owner(repo: Repository):
    assert repo.is_date_free("salao-de-festas", "2030-03-16") is False
    assert repo.is_date_free("salao-de-festas", "2030-04-20") is True


def test_cancel_only_matches_own_apartment(repo: Repository):
    assert repo.cancel_reservation("101", area_id="salao-de-festas", data="2030-03-16") is None
    assert repo.cancel_reservation("101", codigo="RSV-4821") is None
    assert [r.codigo for r in repo.list_reservations("302")] == ["RSV-4821"]
    cancelled = repo.cancel_reservation("101", area_id="quadra", data="2030-03-09")
    assert cancelled is not None and cancelled.codigo == "RSV-1377"
    assert repo.list_reservations("101") == []


def test_new_codes_never_repeat_existing_or_cancelled(repo: Repository):
    repo.cancel_reservation("101", codigo="RSV-1377")
    codes = set()
    for day in range(1, 29):
        result = repo.create_reservation("101", "quadra", f"2031-02-{day:02d}")
        assert result.created
        codes.add(result.reserva.codigo)
    assert len(codes) == 28
    assert not codes & {"RSV-1377", "RSV-4821", "RSV-2950"}


def test_cancelled_slot_can_be_booked_again(repo: Repository):
    repo.cancel_reservation("101", codigo="RSV-1377")
    assert repo.create_reservation("102", "quadra", "2030-03-09").created


def test_restore_keeps_issued_codes(repo: Repository, settings):
    created = repo.create_reservation("101", "quadra", "2031-01-01").reserva.codigo
    seed(repo, settings.dados_dir)
    assert repo.list_reservations("101")[0].codigo == "RSV-1377"
    with repo._read() as conn:
        issued = {r[0] for r in conn.execute("SELECT codigo FROM codigos_emitidos")}
    assert created in issued


def test_concurrent_reservations_have_a_single_winner(repo: Repository):
    def attempt(apto: str):
        return repo.create_reservation(apto, "salao-de-festas", "2030-05-11")

    apartments = ["101", "102", "201", "202", "301", "302"] * 4
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(apartments)) as pool:
        results = list(pool.map(attempt, apartments))
    assert sum(r.created for r in results) == 1
    assert all(r.reason == "indisponivel" for r in results if not r.created)
    total = sum(
        1
        for apto in set(apartments)
        for r in repo.list_reservations(apto)
        if r.area == "salao-de-festas" and r.data == "2030-05-11"
    )
    assert total == 1
