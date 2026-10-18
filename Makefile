# Residencial Aurora — developer commands. Run `make help` to list them.
SHELL := /bin/bash
.DEFAULT_GOAL := help

VERSION := $(shell cat VERSION 2>/dev/null || echo 0.0.0)
export AURORA_VERSION := $(VERSION)

# Host user, so files created by the container in ./var stay writable for you.
export UID := $(shell id -u)
export GID := $(shell id -g)

# Host ports (override them in .env when they are already in use).
-include .env
export API_PORT := $(or $(API_PORT),8000)
export PROMETHEUS_PORT := $(or $(PROMETHEUS_PORT),9090)
export GRAFANA_PORT := $(or $(GRAFANA_PORT),3000)
export SUPPORTED_UBUNTU := 22.04 24.04 26.04

MISE := $(shell command -v mise 2>/dev/null || echo $(HOME)/.local/bin/mise)
RUN := $(MISE) exec --
COMPOSE := docker compose
UP_FLAGS ?=
IMAGE_REPO ?= aurora-api
PLATFORMS ?= linux/amd64,linux/arm64
BUILDER ?= aurora-builder
PYTEST_FLAGS ?= -v
BASE_URL := http://localhost:$(API_PORT)

define banner
	@printf '\n\033[1m==> %s\033[0m\n' "$(1)"
endef

##@ Ajuda
.PHONY: help
help: ## Lista os comandos disponíveis
	@printf '\033[1mResidencial Aurora %s\033[0m — uso: make <alvo>\n' "$(VERSION)"
	@awk 'BEGIN {FS = ":.*##"} /^##@/ {printf "\n\033[1m%s\033[0m\n", substr($$0, 5)} /^[a-zA-Z0-9_-]+:.*##/ {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf '\nPortas: API=%s Prometheus=%s Grafana=%s (altere no .env)\n' "$(API_PORT)" "$(PROMETHEUS_PORT)" "$(GRAFANA_PORT)"

.PHONY: version
version: ## Mostra a versão do projeto (arquivo VERSION)
	@echo $(VERSION)

##@ Ambiente
.PHONY: check-os
check-os: ## Confere se o sistema operacional e a arquitetura são suportados
	@bash scripts/check-os.sh

.PHONY: check-dependencies
check-dependencies: check-os ## Confere as dependências (Docker, Compose, Buildx, mise, uv, jq...)
	@bash scripts/check-deps.sh

.PHONY: requirements
requirements: ## Mostra o arquivo de requisitos do seu sistema
	@f=$$(source scripts/lib.sh; requirements_file); f=$${f:-REQUIREMENTS.md}; echo "$$f"; \
	  (command -v xdg-open >/dev/null && xdg-open "$$f" >/dev/null 2>&1 &) || (command -v open >/dev/null && open "$$f") || true

.PHONY: install
install: check-os ## Instala o mise (no seu usuário), as ferramentas do mise.toml e as dependências Python
	@if [ ! -x "$(MISE)" ]; then \
	  echo "[INFO] Instalando o mise em $$HOME/.local/bin (https://mise.jdx.dev/installing-mise.html)"; \
	  curl -fsSL https://mise.run | sh || { echo "[ERRO] Falha ao instalar o mise. Veja: https://mise.jdx.dev/installing-mise.html" >&2; exit 1; }; \
	fi
	@$(MISE) trust --yes mise.toml >/dev/null 2>&1 || true
	@$(MISE) install || { echo "[ERRO] 'mise install' falhou. Rode '$(MISE) doctor' para diagnosticar." >&2; exit 1; }
	@$(RUN) uv sync || { echo "[ERRO] 'uv sync' falhou. Confira a conexão com o PyPI e o arquivo uv.lock." >&2; exit 1; }
	@echo "[ OK ] Ambiente pronto. Ative o mise no shell: https://mise.jdx.dev/getting-started.html"
	@[ -f .env ] || echo "[WARN] Falta o .env: cp .env.example .env e preencha GOOGLE_API_KEY."

##@ Execução
.PHONY: build
build: check-os ## Gera a imagem Docker da API para a sua plataforma (tag = VERSION)
	$(call banner,Build aurora-api:$(VERSION))
	@$(COMPOSE) build api || { echo "[ERRO] Build falhou. Veja a mensagem acima; confira o Docker com 'make check-dependencies'." >&2; exit 1; }
	@docker tag aurora-api:$(VERSION) aurora-api:latest

.PHONY: build-multiarch
build-multiarch: check-os ## Gera imagens linux/amd64 e linux/arm64 (PUSH=1 IMAGE_REPO=<registro> publica)
	$(call banner,Build multi-arquitetura $(IMAGE_REPO):$(VERSION) [$(PLATFORMS)])
	@docker buildx inspect $(BUILDER) >/dev/null 2>&1 || docker buildx create --name $(BUILDER) --driver docker-container >/dev/null
	@platforms=$$(docker buildx inspect --bootstrap $(BUILDER) | grep -i '^Platforms:'); \
	  for p in $$(echo "$(PLATFORMS)" | tr ',' ' '); do \
	    echo "$$platforms" | grep -q "$$p" || { echo "[ERRO] O builder não suporta $$p (falta emulação QEMU)." >&2; \
	      echo "       ↳ Rode: docker run --privileged --rm tonistiigi/binfmt --install all  (https://docs.docker.com/build/building/multi-platform/)" >&2; exit 1; }; \
	  done
	@docker buildx build --builder $(BUILDER) --platform $(PLATFORMS) \
	  --build-arg AURORA_VERSION=$(VERSION) \
	  -t $(IMAGE_REPO):$(VERSION) -t $(IMAGE_REPO):latest \
	  $(if $(PUSH),--push,) . \
	  || { echo "[ERRO] Build multi-arquitetura falhou. Veja a saída acima." >&2; exit 1; }
	@echo "[ OK ] Imagens $(PLATFORMS) geradas$(if $(PUSH), e publicadas em $(IMAGE_REPO), (cache do builder; use PUSH=1 IMAGE_REPO=<registro> para publicar))."

.PHONY: preflight
preflight: check-os
	@REQUIRE_API_KEY=$(or $(REQUIRE_API_KEY),1) bash scripts/check-env.sh
	@bash scripts/check-ports.sh
	@mkdir -p var

.PHONY: up
up: preflight ## Sobe API, Prometheus e Grafana (primeiro plano; Ctrl+C para parar)
	$(call banner,Subindo Aurora $(VERSION): API $(BASE_URL) | Prometheus :$(PROMETHEUS_PORT) | Grafana :$(GRAFANA_PORT))
	@$(COMPOSE) up --build $(UP_FLAGS) || { code=$$?; [ $$code -eq 130 ] && exit 0; \
	  echo "[ERRO] docker compose up falhou (código $$code). Veja os logs com 'make logs' ou acima." >&2; exit $$code; }

.PHONY: down
down: ## Para e remove os containers (dados em ./var são mantidos)
	@$(COMPOSE) down

.PHONY: restore
restore: preflight-restore ## Restaura reservas e visitantes para os arquivos de dados/ (mantém sessões)
	@$(COMPOSE) run --rm --no-deps --build api python -m aurora.restore

.PHONY: reset
reset: preflight-restore ## Restaura os dados iniciais e apaga todas as sessões
	@$(COMPOSE) run --rm --no-deps --build api python -m aurora.restore --sessions

.PHONY: preflight-restore
preflight-restore: check-os
	@mkdir -p var
	@REQUIRE_API_KEY=0 bash scripts/check-env.sh >/dev/null 2>&1 || touch .env

.PHONY: logs
logs: ## Acompanha os logs da API
	@$(COMPOSE) logs -f api

.PHONY: swagger
swagger: ## Abre o Swagger UI (/docs)
	@echo "$(BASE_URL)/docs"; (command -v xdg-open >/dev/null && xdg-open "$(BASE_URL)/docs" >/dev/null 2>&1 &) || (command -v open >/dev/null && open "$(BASE_URL)/docs") || true

.PHONY: openapi
openapi: ## Exporta a especificação OpenAPI para docs/openapi.json
	@$(RUN) uv run python -c "import json; from aurora.api.main import create_app; print(json.dumps(create_app().openapi(), indent=2, ensure_ascii=False))" > docs/openapi.json
	@echo "[ OK ] docs/openapi.json atualizado."

##@ Testes
define run_tests
	@$(MAKE) --no-print-directory up UP_FLAGS="-d --wait" || { echo "[ERRO] Não foi possível subir a stack para os testes." >&2; exit 1; }
	@status=0; $(1) || status=$$?; \
	  $(MAKE) --no-print-directory down >/dev/null 2>&1; \
	  if [ $$status -eq 0 ]; then printf '\n\033[32m[ OK ] %s: sucesso\033[0m\n' "$(2)"; \
	  else printf '\n\033[31m[ERRO] %s: falhou (código %s). Veja os detalhes acima.\033[0m\n' "$(2)" "$$status"; fi; \
	  exit $$status
endef

.PHONY: test-unit
test-unit: ## Testes unitários (sobe a stack antes e derruba depois)
	$(call banner,Testes unitários)
	$(call run_tests,$(RUN) uv run pytest tests/unit $(PYTEST_FLAGS),Testes unitários)

.PHONY: test-integration
test-integration: ## Testes de integração do fluxo do avaliador (precisa de GOOGLE_API_KEY)
	$(call banner,Testes de integração em $(BASE_URL))
	$(call run_tests,$(MAKE) --no-print-directory restore >/dev/null && AURORA_BASE_URL=$(BASE_URL) $(RUN) uv run pytest tests/integration -m integration $(PYTEST_FLAGS),Testes de integração)

.PHONY: tests
tests: test-unit test-integration ## Unitários + integração

.PHONY: smoke
smoke: ## Roda os cenários C01–C15 via curl (scripts/smoke.sh)
	$(call banner,Smoke test em $(BASE_URL))
	$(call run_tests,$(MAKE) --no-print-directory restore >/dev/null && BASE=$(BASE_URL) $(RUN) bash scripts/smoke.sh,Smoke test)

##@ Qualidade
.PHONY: lint
lint: ## Verifica estilo e erros com ruff
	@$(RUN) uv run ruff check src tests scripts
	@$(RUN) uv run ruff format --check src tests scripts
	@$(RUN) uv run python scripts/gen_toc.py --check

.PHONY: fmt
fmt: ## Formata o código com ruff
	@$(RUN) uv run ruff check --fix src tests scripts
	@$(RUN) uv run ruff format src tests scripts

.PHONY: toc
toc: ## Gera ou atualiza o sumário (TOC) de todos os arquivos .md
	@$(RUN) uv run python scripts/gen_toc.py

.PHONY: check-diagrams
check-diagrams: ## Valida todos os diagramas Mermaid dos arquivos .md (usa Docker)
	@bash scripts/check-mermaid.sh

.PHONY: dashboards
dashboards: ## Regenera os dashboards do Grafana
	@$(RUN) uv run python scripts/gen_dashboards.py

.PHONY: clean
clean: ## Remove caches locais (não apaga ./var)
	@rm -rf .pytest_cache .ruff_cache
	@find . -name __pycache__ -type d -prune -not -path './.venv/*' -exec rm -rf {} +
