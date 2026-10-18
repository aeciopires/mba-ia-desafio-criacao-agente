"""Pending tool confirmations, derived from the persisted session events (Guarantee 1).

A confirmation is pending while an ``adk_request_confirmation`` function call has no
function response with the same id. The API answers a confirmation by sending exactly
that function response; once it is stored the id is no longer pending, so a second
answer with the same id gets 409 and nothing runs again.
"""

from __future__ import annotations

from typing import Any

from google.adk.events.event import Event

REQUEST_CONFIRMATION = "adk_request_confirmation"


def _confirmation_calls(events: list[Event]) -> list[tuple[Any, Event]]:
    calls = []
    for event in events:
        if event.author == "user":
            continue
        for fc in event.get_function_calls():
            if fc.name == REQUEST_CONFIRMATION and fc.id:
                calls.append((fc, event))
    return calls


def _answered_ids(events: list[Event]) -> set[str]:
    answered = set()
    for event in events:
        for fr in event.get_function_responses():
            if fr.name == REQUEST_CONFIRMATION and fr.id:
                answered.add(fr.id)
    return answered


def describe(fc) -> dict:
    """Build the public representation of a confirmation request."""
    args = fc.args or {}
    original = args.get("originalFunctionCall") or {}
    tool_confirmation = args.get("toolConfirmation") or {}
    payload = tool_confirmation.get("payload")
    detalhes: dict[str, Any] = (
        dict(payload) if isinstance(payload, dict) else dict(original.get("args") or {})
    )
    if tool_confirmation.get("hint"):
        detalhes["descricao"] = tool_confirmation["hint"]
    return {"id": fc.id, "acao": original.get("name", "desconhecida"), "detalhes": detalhes}


def pending_confirmations(events: list[Event]) -> list[dict]:
    answered = _answered_ids(events)
    return [describe(fc) for fc, _ in _confirmation_calls(events) if fc.id not in answered]


def original_call_id(events: list[Event], confirmation_id: str) -> str | None:
    for fc, _ in _confirmation_calls(events):
        if fc.id == confirmation_id:
            return ((fc.args or {}).get("originalFunctionCall") or {}).get("id")
    return None


def tool_ran_after(events: list[Event], original_id: str, since_index: int) -> bool:
    """True when the original tool produced a function response after ``since_index``."""
    for event in events[since_index:]:
        for fr in event.get_function_responses():
            if fr.id == original_id and fr.name != REQUEST_CONFIRMATION:
                return True
    return False
