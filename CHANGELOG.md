# Changelog

<!-- TOC -->
**Sumário**

- [Changelog](#changelog)
  - [0.1.0 - 2026-10-17](#010---2026-10-17)
    - [Adicionado](#adicionado)
    - [Alterado](#alterado)
    - [Corrigido](#corrigido)

<!-- TOC -->

Todas as mudanças relevantes do projeto são registradas aqui.

O formato segue o [Keep a Changelog 1.1.0](https://keepachangelog.com/pt-BR/1.1.0/), e o projeto usa [Versionamento Semântico 2.0.0](https://semver.org/lang/pt-BR/). A versão vem do arquivo [VERSION](VERSION).

## [0.1.0] - 2026-10-17

### Adicionado

- API FastAPI com o contrato do `TASK.md`:
  - sessões, mensagens, confirmações e eventos;
  - rotas de verificação de reservas e visitantes;
  - `/health` com a versão e `/metrics`.
- Swagger UI em `/docs`, ReDoc em `/redoc` e `/openapi.json`, com exemplos dos cenários do avaliador. Cópia versionada em `docs/openapi.json` (`make openapi`).
- Assistente com Google ADK 2.11.0:
  - agente principal `aurora_concierge`;
  - especialistas `reservas_agent` e `visitantes_agent` (transferência) e `regulamento_agent` (`AgentTool`).
- `AuroraRunner`: toda mensagem de texto nova começa no agente principal; respostas de confirmação retomam a invocação do agente que as pediu.
- As cinco garantias implementadas em código:
  - confirmação de tool pelo sistema (409 para id não pendente);
  - apartamento vindo da sessão;
  - sessões persistidas em SQLite com `App` resumível;
  - regulamento lido capítulo a capítulo num `AgentTool`;
  - índice único parcial para a exclusividade da reserva.
- Armazenamento SQLite em `./var` (WAL), com cancelamento lógico e tabela de códigos emitidos que nunca é apagada.
- Comandos `python -m aurora` (API) e `python -m aurora.restore [--sessions]`.
- Modelos Gemini configuráveis por agente (`AURORA_MODEL_ROOT`, `AURORA_MODEL_SPECIALIST`, `AURORA_MODEL_RESERVAS`, `AURORA_MODEL_VISITANTES`, `AURORA_MODEL_REGULAMENTO`). Retentativa automática com espera exponencial para 429/5xx.
- Portas configuráveis (`API_PORT`, `PROMETHEUS_PORT`, `GRAFANA_PORT`), com detecção de porta em uso no Makefile e na inicialização da API.
- Mensagens de erro com causa raiz e dica:
  - Makefile e scripts de checagem;
  - inicialização da API;
  - plugin do ADK para erros de modelo e de tool;
  - respostas 502 com o motivo da falha do Gemini.
- Docker multi-arquitetura (`linux/amd64`, `linux/arm64`) com a versão do `VERSION` na tag e no label. Docker Compose com Prometheus e Grafana e dois dashboards provisionados (ADK e Negócio).
- Makefile:
  - checagens: `check-os`, `check-dependencies`, `requirements`;
  - ambiente e execução: `install`, `build`, `build-multiarch`, `up`, `down`, `restore`, `reset`, `logs`;
  - API: `swagger`, `openapi`;
  - testes: `test-unit`, `test-integration`, `tests`, `smoke`;
  - qualidade: `lint`, `fmt`, `dashboards`, `clean`, `version`, `help`.
- Testes unitários com modelo falso (sem cota) e testes de integração do fluxo do avaliador (passos 1 a 14 e cenário C15). Smoke test via `curl` (`scripts/smoke.sh`).
- Documentação em pt-BR:
  - `README.md` e `docs/`;
  - `REQUIREMENTS.md` e requisitos por sistema (Ubuntu 22.04/24.04/26.04 e macOS com Colima);
  - `CONTRIBUTING.md`, `CLAUDE.md` e `PLAN.md`.
- Sumário (TOC) no início de cada arquivo `.md`, gerado por `make toc` (`scripts/gen_toc.py`). O `make lint` e um teste unitário falham se algum sumário estiver desatualizado. Regra registrada no `CLAUDE.md` e no `CONTRIBUTING.md`.
- Guia visual para iniciantes (`docs/guia-visual.md`): 19 diagramas Mermaid (arquitetura, agentes e roteamento, fluxos da API e da confirmação, garantias, estados, modelo de dados, classes, infraestrutura, testes e observabilidade), cada um com analogias do condomínio, e glossário. Diagrama Mermaid resumido no README e em `docs/arquitetura.md`.
- `make check-diagrams` (`scripts/check-mermaid.sh`): valida todos os blocos Mermaid com a imagem oficial `minlag/mermaid-cli`.
- Regras de criação e manutenção dos diagramas e das analogias no `CLAUDE.md` e no `CONTRIBUTING.md`.

### Alterado

- `make toc` (`scripts/gen_toc.py`) agora delimita o sumário com duas marcas `<!-- TOC -->`, compatível com os plugins de TOC dos editores, no lugar de `<!-- TOC -->`/`<!-- /TOC -->`. O script ficou idempotente: remove sumários duplicados, no formato antigo ou colapsados numa linha antes de gravar um único bloco. Regra atualizada no `CLAUDE.md` e no `CONTRIBUTING.md`.
- O sumário passa a listar também o título `#`, com `##` e `###` aninhados, igual à saída dos plugins de TOC.

### Corrigido

- `make test-unit` e `make test-integration` falhavam com `ModuleNotFoundError: No module named 'aurora'` quando o `.venv` tinha sido criado em outro caminho (o shebang de `pytest` apontava para um Python inexistente). Os alvos agora usam `uv run python -m pytest`, e o `make install` recria um `.venv` de outro caminho.


[Unreleased]: https://github.com/aeciopires/mba-ia-desafio-criacao-agente/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/aeciopires/mba-ia-desafio-criacao-agente/releases/tag/v0.1.0
