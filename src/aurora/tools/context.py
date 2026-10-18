"""Resolves the apartment that owns the current session (Guarantee 2).

No tool accepts an apartment argument. The apartment always comes from the session,
which the API creates with ``user_id = apartment`` and ``state['apartamento'] = apartment``.
The model cannot change either value: ``user_id`` is immutable, and no tool or agent
writes the ``apartamento`` state key.
"""

from __future__ import annotations

import logging

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

APARTMENT_STATE_KEY = "apartamento"


class SessionApartmentError(RuntimeError):
    """The session has no consistent owner apartment."""


def get_session_apartment(tool_context: ToolContext) -> str:
    """Return the apartment bound to the session, validating user_id against the state."""
    user_id = tool_context.user_id
    state_value = tool_context.state.get(APARTMENT_STATE_KEY)
    if not user_id or state_value != user_id:
        logger.error(
            "Session %s has inconsistent apartment binding: user_id=%r state=%r",
            tool_context.session.id,
            user_id,
            state_value,
        )
        raise SessionApartmentError(
            "Sessão sem apartamento válido; crie uma nova sessão pela rota POST /sessoes."
        )
    return user_id
