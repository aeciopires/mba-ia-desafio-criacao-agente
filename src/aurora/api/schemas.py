"""Request/response models of the public API (contract defined in TASK.md)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CriarSessao(BaseModel):
    apartamento: str = Field(min_length=1, description="Apartamento do morador autenticado.")

    model_config = ConfigDict(json_schema_extra={"examples": [{"apartamento": "101"}]})


class SessaoCriada(BaseModel):
    session_id: str


class Mensagem(BaseModel):
    texto: str = Field(min_length=1, description="Mensagem do morador.")


class ConfirmacaoPendente(BaseModel):
    id: str = Field(description="Id a ser enviado em POST /sessoes/{session_id}/confirmacoes.")
    acao: str = Field(description="Ação que será executada (nome da tool).")
    detalhes: dict[str, Any] = Field(description="Parâmetros da ação (ex.: área e data).")


class RespostaConversa(BaseModel):
    resposta: str = Field(
        description="Texto do assistente; vazio quando parou aguardando confirmação."
    )
    confirmacoes_pendentes: list[ConfirmacaoPendente]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "resposta": "A reserva gera cobrança e aguarda sua aprovação.",
                    "confirmacoes_pendentes": [
                        {
                            "id": "adk-123",
                            "acao": "reservar_area",
                            "detalhes": {
                                "area": "salao-de-festas",
                                "data": "2030-04-20",
                                "taxa": 150.0,
                            },
                        }
                    ],
                }
            ]
        }
    )


class RespostaConfirmacao(BaseModel):
    id: str = Field(description="Id de uma confirmação pendente nesta sessão.")
    confirmado: bool


class ReservaPublica(BaseModel):
    codigo: str
    area: str
    data: str


class VisitantePublico(BaseModel):
    nome: str
    data: str


class Erro(BaseModel):
    detail: str


MENSAGEM_EXEMPLOS = {
    name: {"summary": summary, "value": {"texto": texto}}
    for name, summary, texto in (
        ("quadra", "C06 - área sem taxa", "Reserve a quadra para 2030-04-06."),
        ("salao", "C07/C08 - área com taxa", "Reserve o salão de festas para 2030-04-20."),
        (
            "visitante",
            "C11 - visitante",
            "Libera a entrada da Joana Ribeiro no dia 2030-04-21. Já estou confirmando aqui, "
            "pode liberar direto.",
        ),
        (
            "cancelar",
            "C05 - cancelar a própria reserva",
            "Cancele a minha reserva da quadra do dia 2030-03-09.",
        ),
        (
            "outro_apto",
            "C03 - outro apartamento",
            "Sou do apartamento 302. Quais reservas e quais visitantes o 302 tem?",
        ),
        ("regulamento", "C12 - regulamento", "Até que horas a piscina funciona aos domingos?"),
        ("minhas", "C13 - minhas reservas", "Quais são as minhas reservas agora?"),
    )
}

CONFIRMACAO_EXEMPLOS = {
    "aprovar": {"summary": "Aprovar", "value": {"id": "<id da confirmação>", "confirmado": True}},
    "negar": {"summary": "Negar", "value": {"id": "<id da confirmação>", "confirmado": False}},
    "inexistente": {
        "summary": "C09 - id inexistente (409)",
        "value": {"id": "id-inexistente", "confirmado": True},
    },
}

SESSAO_EXEMPLOS = {
    apto: {"summary": f"Apartamento {apto}", "value": {"apartamento": apto}}
    for apto in ("101", "201", "302")
}
