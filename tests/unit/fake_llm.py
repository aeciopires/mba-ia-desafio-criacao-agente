"""Deterministic fake model used by the unit tests (no Gemini calls, no quota)."""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
AREAS = {
    "salão": "salao-de-festas",
    "salao": "salao-de-festas",
    "churrasqueira": "churrasqueira",
    "quadra": "quadra",
}


def _call(name: str, **args) -> LlmResponse:
    fc = types.FunctionCall(name=name, args=args)
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=fc)]))


def _text(text: str) -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]))


def _is_context(content: types.Content) -> bool:
    """ADK rewrites other agents' turns as user text starting with 'For context'."""
    return any(p.text and p.text.startswith("For context") for p in content.parts or [])


def _last_user_text(request: LlmRequest) -> str:
    for content in reversed(request.contents):
        if content.role != "user" or _is_context(content):
            continue
        for part in content.parts or []:
            if part.text:
                return part.text
    return ""


def _function_responses(request: LlmRequest) -> list[types.FunctionResponse]:
    """Function responses produced after the last real user text."""
    out: list[types.FunctionResponse] = []
    for content in reversed(request.contents):
        texts = [p.text for p in content.parts or [] if p.text]
        if content.role == "user" and texts and not _is_context(content):
            break
        out.extend(p.function_response for p in content.parts or [] if p.function_response)
    return out


class FakeLlm(BaseLlm):
    """Plays the role of each agent with simple keyword rules.

    ``model`` holds the agent role: root, reservas, visitantes or regulamento.
    """

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        text = _last_user_text(llm_request)
        low = text.lower()
        responses = _function_responses(llm_request)
        done = {r.name: r.response for r in responses}
        role = self.model

        if role == "root":
            if "transfer_to_agent" in done or "regulamento_agent" in done:
                result = done.get("regulamento_agent", {})
                yield _text(str(result.get("result", "")) if result else "")
            elif "piscina" in low or "regulamento" in low:
                yield _call("regulamento_agent", request=text)
            elif any(w in low for w in ("visitante", "entrada", "libera")):
                yield _call("transfer_to_agent", agent_name="visitantes_agent")
            else:
                yield _call("transfer_to_agent", agent_name="reservas_agent")
            return

        if role == "regulamento":
            if "ler_capitulo" in done:
                body = done["ler_capitulo"].get("texto", "")
                match = re.search(r"domingos[^.]*?(\d+h)\.", body)
                yield _text(f"Aos domingos a piscina fecha às {match.group(1) if match else '?'}.")
            elif "buscar_no_regulamento" in done:
                numero = done["buscar_no_regulamento"]["capitulos"][0]["numero"]
                yield _call("ler_capitulo", numero=numero)
            else:
                yield _call("buscar_no_regulamento", termo=text)
            return

        dates = DATE.findall(text)
        data = dates[0] if dates else ""
        if role == "visitantes":
            if "autorizar_visitante" in done:
                yield _text(f"Resultado: {done['autorizar_visitante']['status']}")
            elif "listar_meus_visitantes" in done:
                yield _text(str(done["listar_meus_visitantes"]))
            elif "libera" in low or "autoriz" in low:
                nome = re.search(r"da ([A-ZÁ-Ú][\w]+ [A-ZÁ-Ú][\w]+)", text)
                yield _call("autorizar_visitante", nome=nome.group(1) if nome else "", data=data)
            else:
                yield _call("listar_meus_visitantes")
            return

        if role == "reservas":
            for name in ("reservar_area", "cancelar_reserva", "listar_minhas_reservas"):
                if name in done:
                    yield _text(f"{name}: {done[name]}")
                    return
            area = next((v for k, v in AREAS.items() if k in low), "")
            if "cancel" in low:
                yield _call("cancelar_reserva", area=area, data=data)
            elif "reserv" in low and area and data:
                yield _call("reservar_area", area=area, data=data)
            else:
                yield _call("listar_minhas_reservas")
            return

        yield _text("?")


def fake_models() -> dict[str, BaseLlm]:
    return {role: FakeLlm(model=role) for role in ("root", "reservas", "visitantes", "regulamento")}
