#!/usr/bin/env bash
# Reusable curl helpers for the Residencial Aurora API.
# Usage: source scripts/api.sh   (BASE defaults to http://localhost:${API_PORT:-8000})
#
# Every helper prints the response body on stdout and the HTTP status on stderr,
# so `$(...)` captures only the body.

BASE="${BASE:-http://localhost:${API_PORT:-8000}}"

_aurora_require() {
  for bin in curl jq; do
    command -v "$bin" >/dev/null 2>&1 || {
      echo "[api.sh] ERRO: '$bin' não encontrado. Rode 'make install' (jq vem do mise) ou instale-o." >&2
      return 1
    }
  done
}

# _aurora_call METHOD PATH [JSON_BODY]
_aurora_call() {
  local method="$1" path="$2" body="${3:-}" out code
  _aurora_require || return 1
  if [ -n "$body" ]; then
    out=$(curl -sS -X "$method" "$BASE$path" -H 'Content-Type: application/json' \
      -d "$body" -w $'\n%{http_code}') || {
      echo "[api.sh] ERRO: não foi possível conectar em $BASE. A API está no ar? (make up)" >&2
      return 1
    }
  else
    out=$(curl -sS -X "$method" "$BASE$path" -w $'\n%{http_code}') || {
      echo "[api.sh] ERRO: não foi possível conectar em $BASE. A API está no ar? (make up)" >&2
      return 1
    }
  fi
  code="${out##*$'\n'}"
  AURORA_LAST_STATUS="$code"
  echo "HTTP $code $method $path" >&2
  printf '%s\n' "${out%$'\n'*}"
}

nova_sessao() {  # nova_sessao 101 -> prints the session_id
  _aurora_call POST /sessoes "$(jq -nc --arg a "$1" '{apartamento:$a}')" | jq -r '.session_id'
}

msg() {  # msg SESSION "text"
  _aurora_call POST "/sessoes/$1/mensagens" "$(jq -nc --arg t "$2" '{texto:$t}')"
}

pendente() {  # pendente SESSION "text" -> prints the id of the first pending confirmation
  local body
  body=$(msg "$1" "$2") || return 1
  echo "$body" | jq . >&2
  echo "$body" | jq -r '.confirmacoes_pendentes[0].id // empty'
}

confirmar() {  # confirmar SESSION ID true|false
  _aurora_call POST "/sessoes/$1/confirmacoes" "$(jq -nc --arg i "$2" --argjson c "$3" '{id:$i, confirmado:$c}')"
}

eventos() { _aurora_call GET "/sessoes/$1/eventos"; }
reservas() { _aurora_call GET "/apartamentos/$1/reservas"; }
visitantes() { _aurora_call GET "/apartamentos/$1/visitantes"; }
