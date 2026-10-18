# Observabilidade

<!-- TOC -->
**Sumário**

- [Dashboards](#dashboards)
- [Métricas](#métricas)
<!-- /TOC -->

`make up` sobe o Prometheus (`:9090`) e o Grafana (`:3000`, admin/admin). As portas são configuráveis com `PROMETHEUS_PORT` e `GRAFANA_PORT`. O Prometheus coleta `GET /metrics` da API a cada 10 s. O Grafana já vem com a fonte de dados e dois dashboards na pasta **Aurora**.

> Diagramas e analogias: [guia-visual.md](guia-visual.md).

## Dashboards

| Dashboard | Painéis |
|---|---|
| **Aurora — ADK** | chamadas ao modelo (total e por agente/minuto), tempo médio e p95 de resposta, tokens por agente, erros do modelo por tipo, chamadas de tool por status, transferências entre agentes, tempo por rota HTTP |
| **Aurora — Negócio** (inicial) | apartamentos (vizinhos), sessões, confirmações pendentes, reservas criadas, cobranças e valor cobrado, reservas ativas por apartamento, por data e por área, dia com mais reservas, confirmações aprovadas/negadas, visitantes por apartamento, reservas recusadas por data ocupada, pedidos sobre reservas de outro apartamento |

Os JSON ficam em `observability/grafana/dashboards/` e são gerados por `make dashboards` ([scripts/gen_dashboards.py](../scripts/gen_dashboards.py)).

## Métricas

| Métrica | Tipo | Labels |
|---|---|---|
| `aurora_build_info` | info | `version` |
| `aurora_llm_calls_total` | counter | `agent`, `model` |
| `aurora_llm_latency_seconds` | histogram | `agent` |
| `aurora_llm_tokens_total` | counter | `agent`, `type` |
| `aurora_llm_errors_total` | counter | `agent`, `error` |
| `aurora_tool_calls_total` | counter | `tool`, `status` |
| `aurora_agent_transfers_total` | counter | `to` |
| `aurora_http_request_duration_seconds` | histogram | `route`, `method`, `status` |
| `aurora_reservas_criadas_total` / `aurora_reservas_canceladas_total` | counter | `apartamento`, `area` |
| `aurora_cobrancas_total` / `aurora_cobrancas_valor_reais_total` | counter | `area` |
| `aurora_visitantes_autorizados_total` | counter | `apartamento` |
| `aurora_confirmacoes_total` | counter | `acao`, `resultado` |
| `aurora_confirmacoes_pendentes` | gauge | — |
| `aurora_conflitos_reserva_total` | counter | `area` |
| `aurora_tentativas_outro_apartamento_total` | counter | — |
| `aurora_apartamentos`, `aurora_sessoes` | gauge (lido do banco) | — |
| `aurora_reservas_ativas_por_area` / `_por_data` / `_por_apartamento` | gauge (lido do banco) | `area` / `data` / `apartamento` |
| `aurora_visitantes_por_apartamento` | gauge (lido do banco) | `apartamento` |

Os contadores recomeçam a cada reinício da API. Os gauges "lidos do banco" refletem sempre o estado atual.
