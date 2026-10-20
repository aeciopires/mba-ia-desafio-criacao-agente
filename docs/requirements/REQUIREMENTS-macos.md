# Requisitos — macOS (Intel e Apple Silicon)

<!-- TOC -->
**Sumário**

- [Requisitos — macOS (Intel e Apple Silicon)](#requisitos--macos-intel-e-apple-silicon)
  - [1. Caminho rápido (recomendado)](#1-caminho-rápido-recomendado)
  - [2. Particularidades do macOS](#2-particularidades-do-macos)
  - [3. Instalação manual (instruções oficiais)](#3-instalação-manual-instruções-oficiais)
    - [3.1 Ferramentas base](#31-ferramentas-base)
    - [3.2 Colima, Docker CLI, Compose e Buildx](#32-colima-docker-cli-compose-e-buildx)
    - [3.3 Iniciar o Colima](#33-iniciar-o-colima)
    - [3.4 Build multi-arquitetura (opcional, para `make build-multiarch`)](#34-build-multi-arquitetura-opcional-para-make-build-multiarch)
    - [3.5 mise](#35-mise)
    - [3.6 Python, uv e jq (via mise) e dependências do projeto](#36-python-uv-e-jq-via-mise-e-dependências-do-projeto)
  - [4. Versões de referência](#4-versões-de-referência)
  - [5. Verificação final](#5-verificação-final)
  - [6. Problemas comuns](#6-problemas-comuns)

<!-- TOC -->

Arquiteturas suportadas: **amd64** (Intel) e **arm64** (Apple Silicon). O runtime de containers é o **[Colima](https://github.com/abiosoft/colima)**, uma VM Linux com Docker Engine, usada com o Docker CLI, o Compose e o Buildx. Última revisão: 2026-10-20.

## 1. Caminho rápido (recomendado)

```bash
make check-os              # confirma sistema e arquitetura
make check-dependencies    # lista o que falta e confere se o Colima está rodando
make install               # instala o mise (no seu usuário), as ferramentas do mise.toml e roda `uv sync`
```

O `make install` **não** instala o Colima, o Docker CLI nem as Command Line Tools. Para esses, siga a seção 3.

## 2. Particularidades do macOS

- **Pré-requisito:** [Homebrew](https://brew.sh/), o método de instalação indicado no README do Colima.
- **Recursos da VM:** recomendado `--cpu 4 --memory 6 --disk 30`. Para deixar fixo, use `colima template` ou `~/.colima/default/colima.yaml`.
- **Apple Silicon:** `--vm-type vz` exige macOS 13 ou mais novo. `--vz-rosetta` usa o Rosetta 2 (`softwareupdate --install-rosetta`) para emular `linux/amd64` rapidamente.
- **Montagens:** o Colima monta o `$HOME` com escrita. **Clone o repositório dentro do `$HOME`**, senão os bind mounts `./var` e `./dados` não funcionam (ou configure `--mount`).
- **Portas:** o Colima encaminha as portas publicadas para `localhost`, então `:8000`, `:3000` e `:9090` funcionam como no Linux.
- **Parar e remover:** `colima stop` e `colima delete`.

## 3. Instalação manual (instruções oficiais)

### 3.1 Ferramentas base

```bash
xcode-select --install       # Command Line Tools da Apple: make e git (curl já vem no macOS)
```

Homebrew: <https://brew.sh/>

### 3.2 Colima, Docker CLI, Compose e Buildx

Fonte oficial: <https://github.com/abiosoft/colima#installation>

```bash
brew install colima docker docker-compose docker-buildx

# Registrar os plugins do Docker CLI instalados pelo Homebrew (compose e buildx)
mkdir -p ~/.docker
cat > ~/.docker/config.json <<EOF
{
  "cliPluginsExtraDirs": ["$(brew --prefix)/lib/docker/cli-plugins"]
}
EOF
```

Se `~/.docker/config.json` já existir, apenas acrescente a chave `cliPluginsExtraDirs`.

### 3.3 Iniciar o Colima

```bash
# Intel
colima start --cpu 4 --memory 6 --disk 30

# Apple Silicon (macOS 13+)
colima start --cpu 4 --memory 6 --disk 30 --vm-type vz --vz-rosetta --mount-type virtiofs

docker context use colima    # o Colima cria e seleciona este contexto
brew services start colima   # opcional: iniciar junto com o login
```

O Colima expõe o socket do Docker no seu diretório de usuário, então não é preciso `sudo`.

### 3.4 Build multi-arquitetura (opcional, para `make build-multiarch`)

Fonte oficial: <https://docs.docker.com/build/building/multi-platform/>

```bash
docker run --privileged --rm tonistiigi/binfmt --install all   # QEMU dentro da VM do Colima
docker buildx create --name aurora-builder --driver docker-container --use
```

### 3.5 mise

Fontes oficiais: <https://mise.jdx.dev/installing-mise.html> e <https://mise.jdx.dev/getting-started.html>

```bash
curl -fsSL https://mise.run | sh                      # ou: brew install mise
echo 'eval "$(~/.local/bin/mise activate zsh)"' >> ~/.zshrc
source ~/.zshrc
```

### 3.6 Python, uv e jq (via mise) e dependências do projeto

Fonte oficial do uv: <https://docs.astral.sh/uv/getting-started/installation/>

```bash
mise trust mise.toml
mise install
uv sync
```

## 4. Versões de referência

| Software | Versão fixada / testada | Onde é definida |
|---|---|---|
| Python | 3.14.8 | `mise.toml` (imagem: `python:3.14.8-slim-trixie`) |
| uv | 0.12.24 | `mise.toml` (imagem: `ghcr.io/astral-sh/uv:0.12.24`) |
| jq | 1.8.1 | `mise.toml` |
| Google ADK | 2.11.0 | `pyproject.toml` / `uv.lock` |
| Prometheus | v3.15.0 | `docker-compose.yml` |
| Grafana | 13.2.4 | `docker-compose.yml` |
| Colima | versão estável do Homebrew | Homebrew |
| Docker CLI, Compose e Buildx | versões estáveis do Homebrew (Compose v2 ou mais novo) | Homebrew |

## 5. Verificação final

```bash
colima status
docker context show          # deve mostrar: colima
docker version
docker compose version
docker buildx version
mise --version && uv --version && python --version && jq --version
make check-dependencies
```

## 6. Problemas comuns

| Sintoma | Solução |
|---|---|
| `Cannot connect to the Docker daemon` | `colima start` e `docker context use colima` |
| `docker: 'compose' is not a docker command` | Configure `cliPluginsExtraDirs` (passo 3.2) |
| `Permission denied` / arquivos não aparecem em `./var` | Repositório fora do `$HOME`; mova-o ou configure `--mount` |
| Build ou containers lentos/sem memória | `colima stop && colima start --cpu 4 --memory 8` |
| `A porta 8000 já está em uso` | Troque `API_PORT` (ou `PROMETHEUS_PORT`/`GRAFANA_PORT`) no `.env` |
| `mise: command not found` | Ative o mise no shell (passo 3.5) |
