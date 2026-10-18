"""Generate the Grafana dashboards (observability/grafana/dashboards/*.json).

Run: uv run python scripts/gen_dashboards.py
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "observability" / "grafana" / "dashboards"
DS = {"type": "prometheus", "uid": "prometheus"}


def panel(pid, title, kind, exprs, x, y, w=8, h=8, unit=None, legend=None, instant=False):
    targets = [
        {
            "refId": chr(65 + i),
            "datasource": DS,
            "expr": e,
            "legendFormat": (legend or [""] * len(exprs))[i],
            "instant": instant,
            "range": not instant,
        }
        for i, e in enumerate(exprs)
    ]
    p = {
        "id": pid,
        "title": title,
        "type": kind,
        "datasource": DS,
        "targets": targets,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "fieldConfig": {"defaults": {"unit": unit or "short"}, "overrides": []},
        "options": {},
    }
    if kind == "barchart":
        p["options"] = {"orientation": "horizontal", "xField": None, "showValue": "auto"}
        p["transformations"] = [{"id": "reduce", "options": {"reducers": ["lastNotNull"]}}]
    if kind == "table":
        p["transformations"] = [{"id": "reduce", "options": {"reducers": ["lastNotNull"]}}]
    return p


def dashboard(uid, title, panels):
    return {
        "uid": uid,
        "title": title,
        "tags": ["aurora"],
        "timezone": "browser",
        "schemaVersion": 39,
        "refresh": "10s",
        "time": {"from": "now-6h", "to": "now"},
        "panels": panels,
        "editable": True,
    }


adk = dashboard(
    "aurora-adk",
    "Aurora — ADK",
    [
        panel(1, "Chamadas ao modelo (total)", "stat", ["sum(aurora_llm_calls_total)"], 0, 0, 6, 4),
        panel(
            2,
            "Tempo médio de resposta do modelo",
            "stat",
            ["sum(aurora_llm_latency_seconds_sum) / sum(aurora_llm_latency_seconds_count)"],
            6,
            0,
            6,
            4,
            "s",
        ),
        panel(
            3,
            "Erros do modelo (total)",
            "stat",
            ["sum(aurora_llm_errors_total) or vector(0)"],
            12,
            0,
            6,
            4,
        ),
        panel(4, "Tokens (total)", "stat", ["sum(aurora_llm_tokens_total)"], 18, 0, 6, 4),
        panel(
            5,
            "Chamadas ao modelo por agente (por minuto)",
            "timeseries",
            ["sum by (agent) (rate(aurora_llm_calls_total[5m])) * 60"],
            0,
            4,
            12,
            8,
            legend=["{{agent}}"],
        ),
        panel(
            6,
            "Latência do modelo p95 por agente",
            "timeseries",
            [
                "histogram_quantile(0.95, sum by (le, agent) (rate(aurora_llm_latency_seconds_bucket[5m])))"
            ],
            12,
            4,
            12,
            8,
            "s",
            legend=["{{agent}}"],
        ),
        panel(
            7,
            "Chamadas de tool por tool e status",
            "barchart",
            ["sum by (tool, status) (aurora_tool_calls_total)"],
            0,
            12,
            12,
            9,
            legend=["{{tool}} / {{status}}"],
            instant=True,
        ),
        panel(
            8,
            "Tokens por agente e tipo",
            "barchart",
            ["sum by (agent, type) (aurora_llm_tokens_total)"],
            12,
            12,
            12,
            9,
            legend=["{{agent}} / {{type}}"],
            instant=True,
        ),
        panel(
            9,
            "Transferências entre agentes",
            "barchart",
            ["sum by (to) (aurora_agent_transfers_total)"],
            0,
            21,
            8,
            8,
            legend=["{{to}}"],
            instant=True,
        ),
        panel(
            10,
            "Erros do modelo por agente e tipo",
            "barchart",
            ["sum by (agent, error) (aurora_llm_errors_total)"],
            8,
            21,
            8,
            8,
            legend=["{{agent}} / {{error}}"],
            instant=True,
        ),
        panel(
            11,
            "Tempo médio por rota HTTP",
            "timeseries",
            [
                "sum by (route) (rate(aurora_http_request_duration_seconds_sum[5m])) / "
                "sum by (route) (rate(aurora_http_request_duration_seconds_count[5m]))"
            ],
            16,
            21,
            8,
            8,
            "s",
            legend=["{{route}}"],
        ),
    ],
)

negocio = dashboard(
    "aurora-negocio",
    "Aurora — Negócio",
    [
        panel(1, "Apartamentos (vizinhos)", "stat", ["aurora_apartamentos"], 0, 0, 4, 4),
        panel(2, "Sessões criadas", "stat", ["aurora_sessoes"], 4, 0, 4, 4),
        panel(3, "Confirmações pendentes", "stat", ["aurora_confirmacoes_pendentes"], 8, 0, 4, 4),
        panel(
            4,
            "Reservas criadas pelo assistente",
            "stat",
            ["sum(aurora_reservas_criadas_total) or vector(0)"],
            12,
            0,
            4,
            4,
        ),
        panel(
            5,
            "Cobranças realizadas",
            "stat",
            ["sum(aurora_cobrancas_total) or vector(0)"],
            16,
            0,
            4,
            4,
        ),
        panel(
            6,
            "Valor cobrado",
            "stat",
            ["sum(aurora_cobrancas_valor_reais_total) or vector(0)"],
            20,
            0,
            4,
            4,
            "currencyBRL",
        ),
        panel(
            7,
            "Reservas ativas por apartamento",
            "barchart",
            ["aurora_reservas_ativas_por_apartamento"],
            0,
            4,
            8,
            9,
            legend=["{{apartamento}}"],
            instant=True,
        ),
        panel(
            8,
            "Reservas ativas por data",
            "barchart",
            ["aurora_reservas_ativas_por_data"],
            8,
            4,
            8,
            9,
            legend=["{{data}}"],
            instant=True,
        ),
        panel(
            9,
            "Dia com mais reservas",
            "table",
            ["topk(1, aurora_reservas_ativas_por_data)"],
            16,
            4,
            8,
            4,
            legend=["{{data}}"],
            instant=True,
        ),
        panel(
            10,
            "Reservas ativas por área",
            "barchart",
            ["aurora_reservas_ativas_por_area"],
            16,
            8,
            8,
            5,
            legend=["{{area}}"],
            instant=True,
        ),
        panel(
            11,
            "Reservas criadas por apartamento e área",
            "barchart",
            ["sum by (apartamento, area) (aurora_reservas_criadas_total)"],
            0,
            13,
            8,
            8,
            legend=["{{apartamento}} / {{area}}"],
            instant=True,
        ),
        panel(
            12,
            "Confirmações respondidas",
            "barchart",
            ["sum by (acao, resultado) (aurora_confirmacoes_total)"],
            8,
            13,
            8,
            8,
            legend=["{{acao}} / {{resultado}}"],
            instant=True,
        ),
        panel(
            13,
            "Visitantes autorizados por apartamento",
            "barchart",
            ["aurora_visitantes_por_apartamento"],
            16,
            13,
            8,
            8,
            legend=["{{apartamento}}"],
            instant=True,
        ),
        panel(
            14,
            "Reservas recusadas por data ocupada",
            "timeseries",
            ["sum by (area) (increase(aurora_conflitos_reserva_total[1h]))"],
            0,
            21,
            12,
            8,
            legend=["{{area}}"],
        ),
        panel(
            15,
            "Pedidos sobre reservas de outro apartamento",
            "timeseries",
            ["increase(aurora_tentativas_outro_apartamento_total[1h])"],
            12,
            21,
            12,
            8,
            legend=["tentativas"],
        ),
    ],
)

OUT.mkdir(parents=True, exist_ok=True)
for name, dash in (("aurora-adk.json", adk), ("aurora-negocio.json", negocio)):
    (OUT / name).write_text(json.dumps(dash, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT / name}")
