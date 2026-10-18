# Requisitos — Ubuntu 22.04 LTS (Jammy Jellyfish)

<!-- TOC -->
**Sumário**

- [1. Caminho rápido (recomendado)](#1-caminho-rápido-recomendado)
- [2. Particularidades do Ubuntu 22.04](#2-particularidades-do-ubuntu-2204)
- [3. Instalação manual (instruções oficiais)](#3-instalação-manual-instruções-oficiais)
  - [3.1 Pacotes base](#31-pacotes-base)
  - [3.2 Docker Engine, Compose v2 e Buildx](#32-docker-engine-compose-v2-e-buildx)
  - [3.3 Docker sem `sudo`](#33-docker-sem-sudo)
  - [3.4 Build multi-arquitetura (opcional, para `make build-multiarch`)](#34-build-multi-arquitetura-opcional-para-make-build-multiarch)
  - [3.5 mise](#35-mise)
  - [3.6 Python, uv e jq (via mise) e dependências do projeto](#36-python-uv-e-jq-via-mise-e-dependências-do-projeto)
- [4. Versões de referência](#4-versões-de-referência)
- [5. Verificação final](#5-verificação-final)
- [6. Problemas comuns](#6-problemas-comuns)
<!-- /TOC -->

Arquiteturas suportadas: **amd64** (x86_64) e **arm64** (aarch64). Última revisão: 2026-10-17.

## 1. Caminho rápido (recomendado)

```bash
make check-os              # confirma sistema e arquitetura
make check-dependencies    # lista o que falta, com a URL oficial de cada item
make install               # instala o mise (no seu usuário), as ferramentas do mise.toml e roda `uv sync`
```

O `make install` **não** instala o Docker nem pacotes do sistema (isso exige `sudo`). Para esses, siga a seção 3.

## 2. Particularidades do Ubuntu 22.04

- O Ubuntu 22.04 traz pacotes antigos (`docker.io`, `docker-compose`, `podman-docker`, `containerd`, `runc`) que conflitam com o Docker oficial. Remova-os antes, como mostra o passo 3.1.
- O Python do sistema é 3.10; o projeto usa o Python 3.12 instalado pelo mise. Não é preciso mexer no Python do sistema.
- O `jq` do apt (1.6) funciona, mas o projeto usa o `jq` fixado no `mise.toml`.

## 3. Instalação manual (instruções oficiais)

### 3.1 Pacotes base

```bash
sudo apt-get update
sudo apt-get install -y make git curl ca-certificates
```

### 3.2 Docker Engine, Compose v2 e Buildx

Fonte oficial: <https://docs.docker.com/engine/install/ubuntu/>

```bash
# Remover pacotes conflitantes (pode não haver nenhum)
sudo apt remove $(dpkg --get-selections docker.io docker-compose docker-compose-v2 docker-doc docker-buildx podman-docker containerd runc | cut -f1)

# Chave GPG e repositório oficial da Docker
sudo apt update
sudo apt install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update

# Pacotes (o codinome deste sistema é `jammy`)
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl status docker      # se estiver parado: sudo systemctl start docker
```

### 3.3 Docker sem `sudo`

Fonte oficial: <https://docs.docker.com/engine/install/linux-postinstall/>

```bash
sudo groupadd docker 2>/dev/null || true
sudo usermod -aG docker $USER
newgrp docker                     # ou saia e entre de novo na sessão
docker run hello-world
```

### 3.4 Build multi-arquitetura (opcional, para `make build-multiarch`)

Fonte oficial: <https://docs.docker.com/build/building/multi-platform/>

```bash
docker run --privileged --rm tonistiigi/binfmt --install all   # emulação QEMU
docker buildx create --name aurora-builder --driver docker-container --use
```

### 3.5 mise

Fontes oficiais: <https://mise.jdx.dev/installing-mise.html> e <https://mise.jdx.dev/getting-started.html>

```bash
curl -fsSL https://mise.run | sh                       # instala em ~/.local/bin/mise
echo 'eval "$(~/.local/bin/mise activate bash)"' >> ~/.bashrc   # ativação no shell (bash)
source ~/.bashrc
```

### 3.6 Python, uv e jq (via mise) e dependências do projeto

Fonte oficial do uv: <https://docs.astral.sh/uv/getting-started/installation/>

```bash
mise trust mise.toml
mise install          # Python, uv e jq nas versões do mise.toml
uv sync               # dependências Python (uv.lock)
```

## 4. Versões de referência

| Software | Versão fixada / testada | Onde é definida |
|---|---|---|
| Python | 3.12.15 | `mise.toml` (imagem: `python:3.12.15-slim-trixie`) |
| uv | 0.12.24 | `mise.toml` (imagem: `ghcr.io/astral-sh/uv:0.12.24`) |
| jq | 1.8.1 | `mise.toml` |
| Google ADK | 2.11.0 | `pyproject.toml` / `uv.lock` |
| Prometheus | v3.13.4 | `docker-compose.yml` |
| Grafana | 13.0.1 | `docker-compose.yml` |
| Docker Engine | 29.x (testado com 29.9.1) | sistema operacional |
| Docker Compose | v2 plugin (testado com v5.6.0) | sistema operacional |
| Docker Buildx | testado com v0.38.0 | sistema operacional |

## 5. Verificação final

```bash
docker version
docker compose version
docker buildx version
mise --version && uv --version && python --version && jq --version
make check-dependencies
```

## 6. Problemas comuns

| Sintoma | Solução |
|---|---|
| `permission denied ... /var/run/docker.sock` | Passo 3.3 (grupo `docker`) e abra um novo terminal |
| `Cannot connect to the Docker daemon` | `sudo systemctl start docker` |
| `mise: command not found` | Ative o mise no shell (passo 3.5) ou use `~/.local/bin/mise` |
| `A porta 8000 já está em uso` | Troque `API_PORT` (ou `PROMETHEUS_PORT`/`GRAFANA_PORT`) no `.env` |
| `Permission denied` em `./var` | `sudo chown -R $(id -u):$(id -g) var` |
