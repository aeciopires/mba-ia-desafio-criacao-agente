# API

<!-- TOC -->
**Sumário**

- [Swagger / OpenAPI](#swagger--openapi)
- [Rotas](#rotas)
  - [`confirmacoes_pendentes`](#confirmacoes_pendentes)
  - [Eventos](#eventos)
  - [Erros](#erros)
<!-- /TOC -->

Contrato definido no `TASK.md`. Todas as rotas recebem e devolvem JSON. Rotas com `{session_id}` respondem `404` quando a sessão não existe.

> Diagramas e analogias: [guia-visual.md](guia-visual.md).

## Swagger / OpenAPI

| URL | Conteúdo |
|---|---|
| `http://localhost:8000/docs` | Swagger UI interativo (`make swagger`) |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/openapi.json` | Especificação OpenAPI gerada pelo FastAPI |
| [openapi.json](openapi.json) | Cópia versionada (`make openapi`) |

No Swagger, cada rota de conversa traz exemplos prontos com os cenários do avaliador. Basta abrir a rota, clicar em **Try it out**, escolher o exemplo e clicar em **Execute**. `AURORA_ENABLE_DOCS=false` desliga essas rotas.

## Rotas

| Método e caminho | Sucesso | Erros |
|---|---|---|
| `POST /sessoes` `{"apartamento": "101"}` | `201 {"session_id": "..."}` | `422` corpo inválido ou apartamento inexistente |
| `POST /sessoes/{id}/mensagens` `{"texto": "..."}` | `200 {"resposta", "confirmacoes_pendentes"}` | `404`, `502` falha no modelo |
| `POST /sessoes/{id}/confirmacoes` `{"id": "...", "confirmado": true}` | `200` (mesmo formato) | `404`, `409` id não pendente, `502` |
| `GET /sessoes/{id}/eventos` | `200` lista completa de eventos, em ordem | `404` |
| `GET /apartamentos/{n}/reservas` | `200 [{"codigo", "area", "data"}]` (só ativas) | — |
| `GET /apartamentos/{n}/visitantes` | `200 [{"nome", "data"}]` | — |
| `GET /health` | `200 {"status": "ok", "version": "0.1.0"}` | — |
| `GET /metrics` | métricas no formato Prometheus | — |

### `confirmacoes_pendentes`

```json
{
  "id": "adk-87155355-000b-4619-93d4-ca14ae7d23e6",
  "acao": "reservar_area",
  "detalhes": {
    "area": "salao-de-festas",
    "data": "2030-04-20",
    "taxa": 150.0,
    "descricao": "Reservar Salão de festas em 2030-04-20 gera cobrança de R$ 150,00 para o apartamento 101."
  }
}
```

| `acao` | `detalhes` |
|---|---|
| `reservar_area` | `area`, `data`, `taxa`, `descricao` |
| `autorizar_visitante` | `nome`, `data`, `descricao` |

`resposta` vem vazia quando a execução parou esperando confirmação.

### Eventos

`GET /sessoes/{id}/eventos` devolve `Event.model_dump(mode="json", by_alias=True, exclude_none=True)` de cada evento do ADK: autor, conteúdo (texto, `functionCall`, `functionResponse`), ações e timestamps.

### Erros

Erros seguem o formato `{"detail": "..."}`. Os de modelo (502) incluem o tipo do erro e uma dica, por exemplo cota esgotada ou chave inválida.
