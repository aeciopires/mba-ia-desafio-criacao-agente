# Changelog

<!-- TOC -->
**Sumário**

- [Changelog](#changelog)
  - [\[0.2.1\] - 2026-10-20](#021---2026-10-20)
    - [Alterado](#alterado)
    - [Corrigido](#corrigido)
  - [\[0.2.0\] - 2026-10-20](#020---2026-10-20)
    - [Alterado](#alterado-1)
  - [\[0.1.0\] - 2026-10-17](#010---2026-10-17)
    - [Adicionado](#adicionado)
    - [Alterado](#alterado-2)
    - [Corrigido](#corrigido-1)

<!-- TOC -->

Todas as mudanças relevantes do projeto são registradas aqui.

O formato segue o [Keep a Changelog 1.1.0](https://keepachangelog.com/pt-BR/1.1.0/), e o projeto usa [Versionamento Semântico 2.0.0](https://semver.org/lang/pt-BR/). A versão vem do arquivo [VERSION](VERSION).

## [0.2.1] - 2026-10-20

### Alterado

- Prometheus `v3.13.4` → `v3.15.0` e Grafana `13.0.1` → `13.2.4` no `docker-compose.yml`. Pelas notas de versão, nada incompatível com a configuração do projeto: o Prometheus 3.15 deprecia `--log.level` e o 3.14 o parâmetro `stats` da API de consulta, que o projeto não usa; o Grafana 13.2 desliga por padrão os *scripted dashboards*, que o projeto também não usa (os dashboards são provisionados por arquivo).
- Requisitos do Ubuntu unificados em `docs/requirements/REQUIREMENTS-ubuntu.md` (antes um arquivo por versão: `-22.04.md`, `-24.04.md` e `-26.04.md`). As diferenças entre 22.04, 24.04 e 26.04 (codinome, Python do sistema, pacotes conflitantes, AppArmor, repositório apt da Docker) ficam numa tabela e numa subseção por versão. `make check-os` e `make requirements` apontam para o arquivo único em qualquer Ubuntu suportado.

### Corrigido

- Os requisitos do Ubuntu mandavam remover os pacotes conflitantes no "passo 3.1", mas a remoção fica no passo 3.2.
- `make toc` quebrava com `FileNotFoundError` quando um `.md` tinha sido apagado mas a remoção ainda não estava no índice do Git. Agora esses arquivos são ignorados.
- `make check-diagrams` informava `[ OK ] 0 diagramas Mermaid válidos` quando a extração dos diagramas falhava. Agora ignora arquivos apagados e falha com `[ERRO]` se a extração quebrar.

## [0.2.0] - 2026-10-20

### Alterado

- Python 3.12.15 → 3.14.8:
  - `mise.toml` e `.python-version` fixados em 3.14.8;
  - imagens base do `Dockerfile` `python:3.12.15-slim-trixie` → `python:3.14.8-slim-trixie`;
  - `requires-python` passa de `>=3.12` para `>=3.14` e o Ruff usa `target-version = "py314"`; o `uv.lock` foi refeito sem atualizar nenhum pacote (só saíram as marcas e wheels de Python < 3.14);
  - código ajustado pelo Ruff para a sintaxe do 3.14 (`except A, B:` da PEP 758 e `AsyncGenerator[T]` sem o segundo parâmetro);
  - README, `REQUIREMENTS.md`, arquivos de requisitos por sistema (revisão de 2026-10-20), `PLAN.md`, `CLAUDE.md` atualizados.
- Ambientes locais com `.venv` em Python 3.12 são recriados automaticamente pelo `make install` (`uv sync`).

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
