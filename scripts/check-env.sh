#!/usr/bin/env bash
# Validates the .env file before starting the stack.
set -uo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=scripts/lib.sh
. scripts/lib.sh

if [ ! -f .env ]; then
  err "Arquivo .env não encontrado."
  hint "Crie com: cp .env.example .env   e preencha GOOGLE_API_KEY (chave do Google AI Studio)."
  exit 1
fi
key="$(grep -E '^GOOGLE_API_KEY=' .env | tail -1 | cut -d= -f2- | tr -d '"'"'"' ')"
if [ -z "$key" ]; then
  if [ "${REQUIRE_API_KEY:-1}" = "1" ]; then
    err "GOOGLE_API_KEY está vazia no .env: as rotas de conversa vão falhar."
    hint "Gere uma chave em https://aistudio.google.com/apikey e preencha GOOGLE_API_KEY no .env."
    exit 1
  fi
  warn "GOOGLE_API_KEY vazia (permitido para este alvo)."
fi
ok ".env encontrado."
