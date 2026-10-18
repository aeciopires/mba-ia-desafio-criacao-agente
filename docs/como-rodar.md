# Como rodar

<!-- TOC -->
**Sumário**

- [1. Pré-requisitos](#1-pré-requisitos)
- [2. Configuração](#2-configuração)
  - [Portas](#portas)
  - [Modelos e cotas do Gemini](#modelos-e-cotas-do-gemini)
- [3. Subir e restaurar](#3-subir-e-restaurar)
- [4. Imagens Docker](#4-imagens-docker)
- [Diagnóstico de erros](#diagnóstico-de-erros)
<!-- /TOC -->

## 1. Pré-requisitos

Siga o arquivo do seu sistema, indicado em [REQUIREMENTS.md](../REQUIREMENTS.md):

| Sistema | Arquivo |
|---|---|
| Ubuntu 22.04 | [requirements/REQUIREMENTS-ubuntu-22.04.md](requirements/REQUIREMENTS-ubuntu-22.04.md) |
| Ubuntu 24.04 | [requirements/REQUIREMENTS-ubuntu-24.04.md](requirements/REQUIREMENTS-ubuntu-24.04.md) |
| Ubuntu 26.04 | [requirements/REQUIREMENTS-ubuntu-26.04.md](requirements/REQUIREMENTS-ubuntu-26.04.md) |
| macOS (Intel e Apple Silicon) | [requirements/REQUIREMENTS-macos.md](requirements/REQUIREMENTS-macos.md) |

```bash
make check-os
make check-dependencies
make install
```

## 2. Configuração

```bash
cp .env.example .env
# edite .env e preencha GOOGLE_API_KEY
```

A tabela completa de variáveis está no [README](../README.md#variáveis-do-env). Variáveis vazias usam o valor padrão.

### Portas

Os serviços publicam três portas no host. Todas podem ser trocadas no `.env`:

| Serviço | Variável | Padrão |
|---|---|---|
| API | `API_PORT` | 8000 |
| Prometheus | `PROMETHEUS_PORT` | 9090 |
| Grafana | `GRAFANA_PORT` | 3000 |

Antes de subir, o `make up` testa as portas (`scripts/check-ports.sh`). Se alguma estiver ocupada, ele mostra o processo e sugere outro valor:

```
[ERRO] A porta 8000 (API_PORT) já está em uso por python (pid 12345).
       ↳ Escolha outra porta no .env, por exemplo: API_PORT=8001
```

Dentro do container a API sempre escuta na 8000; `API_PORT` só muda a porta publicada no host. Fora do Docker (`uv run python -m aurora`), `API_PORT` é a porta em que o Uvicorn escuta, e o programa também recusa uma porta ocupada com uma mensagem clara.

### Modelos e cotas do Gemini

| Variável | Padrão | Agente |
|---|---|---|
| `AURORA_MODEL_ROOT` | `gemini-3.1-flash-lite` | `aurora_concierge` |
| `AURORA_MODEL_SPECIALIST` | `gemini-2.5-flash` | padrão dos especialistas |
| `AURORA_MODEL_RESERVAS` | = specialist | `reservas_agent` |
| `AURORA_MODEL_VISITANTES` | = specialist | `visitantes_agent` |
| `AURORA_MODEL_REGULAMENTO` | = specialist | `regulamento_agent` |

Chaves gratuitas do AI Studio têm limites **por modelo**, por minuto e por dia, e eles mudam com frequência ([limites oficiais](https://ai.google.dev/gemini-api/docs/rate-limits); veja os seus em <https://aistudio.google.com>). O fluxo do avaliador faz algumas dezenas de chamadas ao modelo. Com chave gratuita, dividir os agentes entre modelos diferentes divide também as cotas. Exemplo usado no desenvolvimento:

```
AURORA_MODEL_ROOT=gemini-3.1-flash-lite
AURORA_MODEL_RESERVAS=gemini-3.5-flash-lite
AURORA_MODEL_VISITANTES=gemini-2.5-flash-lite
AURORA_MODEL_REGULAMENTO=gemini-2.5-flash
```

As chamadas com erro 429/5xx são repetidas automaticamente com espera exponencial (2 s, 4 s, 8 s, 16 s e 32 s). Modelos disponíveis: <https://ai.google.dev/gemini-api/docs/models>.

## 3. Subir e restaurar

```bash
make restore      # reservas e visitantes = dados/ (sessões mantidas)
make up           # primeiro plano; Ctrl+C para parar
```

| Comando | O que faz |
|---|---|
| `make up` | Constrói a imagem `aurora-api:<VERSION>` e sobe API, Prometheus e Grafana |
| `make up UP_FLAGS="-d --wait"` | Sobe em segundo plano e espera os healthchecks |
| `make down` | Para e remove os containers (mantém `./var`) |
| `make restore` | Restaura reservas e visitantes; mantém sessões e códigos já emitidos |
| `make reset` | Restaura e apaga todas as sessões |
| `make logs` | Acompanha os logs da API |
| `make swagger` | Abre `http://localhost:<API_PORT>/docs` |

Sem Docker:

```bash
uv run python -m aurora.restore            # ou --sessions para apagar as sessões
uv run python -m aurora                    # API em http://localhost:${API_PORT:-8000}
```

## 4. Imagens Docker

| Comando | Resultado |
|---|---|
| `make build` | Imagem da sua plataforma, tags `aurora-api:<VERSION>` e `latest` |
| `make build-multiarch` | Valida o build `linux/amd64` + `linux/arm64` com `docker buildx` |
| `make build-multiarch PUSH=1 IMAGE_REPO=ghcr.io/<usuario>/aurora-api` | Publica o manifesto multi-arquitetura |

A versão vem sempre do arquivo [VERSION](../VERSION): é usada na tag, no label `org.opencontainers.image.version`, em `GET /health` e na métrica `aurora_build_info`.

## Diagnóstico de erros

Todas as mensagens seguem o formato `[ERRO] causa` + `↳ o que fazer`.

| Onde | Mensagem | Causa raiz e correção |
|---|---|---|
| `make check-os` | `Sistema não suportado` | Fora de Ubuntu 22.04/24.04/26.04 ou macOS. `SKIP_OS_CHECK=1` força. |
| `make check-dependencies` | `docker não encontrado` / `daemon não responde` | Instale ou inicie o Docker (Linux: `systemctl start docker`; macOS: `colima start`). |
| `make up` | `.env não encontrado` / `GOOGLE_API_KEY está vazia` | `cp .env.example .env` e preencha a chave. |
| `make up` | `A porta X já está em uso` | Troque a porta no `.env`. |
| API (502) | `RESOURCE_EXHAUSTED` | Cota do modelo. Espere ou troque o modelo do agente indicado no log. |
| API (502) | `API key not valid` / `PERMISSION_DENIED` | Chave errada ou de outro produto. Use uma chave do AI Studio. |
| API (502) | `404 ... model` | Nome de modelo inexistente em `AURORA_MODEL_*`. |
| API (500) | `A confirmação foi registrada, mas a ação não executou` | Roteamento do ADK; veja o log `Confirmation ... was stored but the tool did not run`. |
| API (log) | `Não foi possível abrir o banco SQLite` | Permissão em `./var`: `sudo chown -R $(id -u):$(id -g) var`. |
| API (log) | `Arquivo de dados ausente` | `./dados` não montado ou `AURORA_DADOS_DIR` errado. |
| `make restore` | `[restore] ERRO: ...` | Mostra o arquivo ou a permissão com problema. |

Para mais detalhes: `LOG_LEVEL=DEBUG` no `.env` e `make logs`. Os logs mostram cada chamada de modelo e de tool que falhou, com agente, modelo e argumentos.
