# Testes

<!-- TOC -->
**Sumário**

- [Unitários](#unitários)
- [Integração](#integração)
- [Manuais](#manuais)
<!-- /TOC -->

| Comando | O que roda | Usa o Gemini? |
|---|---|---|
| `make test-unit` | `tests/unit` | Não: modelo falso determinístico ([fake_llm.py](../tests/unit/fake_llm.py)) |
| `make test-integration` | `tests/integration`: fluxo do avaliador, passos 1 a 14, mais o C15 | Sim, precisa de `GOOGLE_API_KEY` |
| `make tests` | Os dois acima | Sim |
| `make smoke` | [scripts/smoke.sh](../scripts/smoke.sh): cenários C01–C15 via `curl` | Sim |

Os alvos de teste fazem `make up UP_FLAGS="-d --wait"` antes, rodam os testes, fazem `make down` depois (mesmo com falha) e mostram o resultado. `test-integration` e `smoke` também rodam `make restore` antes.

> Diagramas e analogias: [guia-visual.md](guia-visual.md).

## Unitários

| Arquivo | Cobertura |
|---|---|
| `test_repository.py` | seed, filtros por apartamento, códigos únicos (inclusive após cancelamento e restore), 24 threads disputando a mesma reserva |
| `test_regulamento.py` | 14 capítulos, `ler_capitulo` só devolve um capítulo, instrução do agente principal sem o regulamento |
| `test_api.py` | contrato (201/200/404/409/422), garantias 1, 2, 4 e 5 pela API, roteamento da mensagem nova para o agente principal, OpenAPI |
| `test_persistence.py` | Garantia 3: sessão e confirmação pendente sobrevivem à recriação do runtime |
| `test_project.py` | `VERSION` = `__version__` = `CHANGELOG.md`, arquivos de requisitos por sistema, `docs/openapi.json` atualizado, ponteiros do README existentes, `dados/` intacto |

Para rodar um teste específico sem subir a stack:

```bash
uv run pytest tests/unit -k concurrent -v
```

## Integração

`tests/integration/test_fluxo_avaliador.py` reproduz o fluxo do avaliador contra a API em `AURORA_BASE_URL` (padrão `http://localhost:${API_PORT}`):

- **Perguntas do assistente:** quando o assistente pergunta em vez de agir, o teste responde "Sim, pode prosseguir..." (até 3 tentativas), como o avaliador faria.
- **Reinício (passo 13 e C15):** `docker compose stop api && docker compose up -d --wait api`. Para trocar o comando, use `AURORA_RESTART_CMD`.
- **Passo 14:** as duas aprovações são disparadas ao mesmo tempo com `asyncio.gather`.

Os testes consomem algumas dezenas de chamadas ao modelo. Com chave gratuita, veja [Modelos e cotas](como-rodar.md#modelos-e-cotas-do-gemini).

## Manuais

Passo a passo com Swagger e `curl`: [cenarios-de-teste.md](cenarios-de-teste.md).
