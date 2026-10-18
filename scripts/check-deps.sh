#!/usr/bin/env bash
# Checks the software required to build, run and test the project.
set -uo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=scripts/lib.sh
. scripts/lib.sh

req="$(requirements_file)"; req="${req:-REQUIREMENTS.md}"
missing=0
MISE_BIN="$(command -v mise || echo "$HOME/.local/bin/mise")"

check() {  # check NAME COMMAND URL
  local name="$1" cmd="$2" url="$3" out
  if out=$(eval "$cmd" 2>&1); then
    ok "$name: $(echo "$out" | head -1)"
  else
    err "$name não encontrado ou não funciona."
    hint "Instalação oficial: $url"
    hint "Passo a passo para o seu sistema: $req"
    missing=$((missing + 1))
  fi
}

check make "make --version" "https://www.gnu.org/software/make/"
check git "git --version" "https://git-scm.com/downloads"
check curl "curl --version" "https://curl.se/download.html"
if [ "$(uname -s)" = "Darwin" ]; then
  check colima "colima version" "https://github.com/abiosoft/colima#installation"
  if command -v colima >/dev/null 2>&1 && ! colima status >/dev/null 2>&1; then
    err "Colima instalado, mas parado."
    hint "Inicie com: colima start --cpu 4 --memory 6 --disk 30 (veja $req)"
    missing=$((missing + 1))
  fi
  docker_url="https://github.com/abiosoft/colima#installation"
else
  docker_url="https://docs.docker.com/engine/install/ubuntu/"
fi
check docker "docker --version" "$docker_url"
if command -v docker >/dev/null 2>&1; then
  if ! docker info >/dev/null 2>&1; then
    err "O Docker está instalado, mas o daemon não responde (ou falta permissão no socket)."
    if [ "$(uname -s)" = "Darwin" ]; then
      hint "Confira 'colima status' e 'docker context use colima'."
    else
      hint "Inicie o serviço (sudo systemctl start docker) e use o Docker sem sudo: https://docs.docker.com/engine/install/linux-postinstall/"
    fi
    missing=$((missing + 1))
  fi
fi
check "docker compose" "docker compose version" "https://docs.docker.com/compose/install/"
check "docker buildx" "docker buildx version" "https://docs.docker.com/build/building/multi-platform/"
check mise "$MISE_BIN --version" "https://mise.jdx.dev/installing-mise.html (ou rode: make install)"
if [ -x "$MISE_BIN" ]; then
  check uv "$MISE_BIN exec -- uv --version" "https://docs.astral.sh/uv/getting-started/installation/ (ou rode: make install)"
  check jq "$MISE_BIN exec -- jq --version" "https://jqlang.org/download/ (ou rode: make install)"
  check python "$MISE_BIN exec -- python --version" "https://mise.jdx.dev/lang/python.html (ou rode: make install)"
fi

if [ "$missing" -gt 0 ]; then
  err "$missing dependência(s) com problema. Corrija os itens acima e rode 'make check-dependencies' de novo."
  exit 1
fi
ok "Todas as dependências estão disponíveis."
