#!/usr/bin/env bash
# Fails with a clear message when a host port needed by docker compose is already in use.
set -uo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=scripts/lib.sh
. scripts/lib.sh

# Ports already published by this compose project are not a conflict.
own_ports="$(docker compose ps --format '{{.Publishers}}' 2>/dev/null | grep -oE '0\.0\.0\.0:[0-9]+' | cut -d: -f2 | sort -u | tr '\n' ' ')"

port_busy() {
  (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

who_uses() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | awk 'NR==2 {print $1" (pid "$2")"}'
  elif command -v ss >/dev/null 2>&1; then
    ss -ltnpH "sport = :$1" 2>/dev/null | grep -oE 'users:\(\("[^"]+' | cut -d'"' -f2 | head -1
  fi
}

conflicts=0
for spec in "API_PORT:${API_PORT:-8000}" "PROMETHEUS_PORT:${PROMETHEUS_PORT:-9090}" "GRAFANA_PORT:${GRAFANA_PORT:-3000}"; do
  var="${spec%%:*}"; port="${spec##*:}"
  if [[ " $own_ports " == *" $port "* ]]; then
    continue
  fi
  if port_busy "$port"; then
    user="$(who_uses "$port")"
    err "A porta $port ($var) já está em uso${user:+ por $user}."
    hint "Escolha outra porta no .env, por exemplo: $var=$((port + 1))   (depois rode o comando de novo)"
    conflicts=$((conflicts + 1))
  fi
done
[ "$conflicts" -eq 0 ] && ok "Portas livres: API=${API_PORT:-8000} Prometheus=${PROMETHEUS_PORT:-9090} Grafana=${GRAFANA_PORT:-3000}"
exit $(( conflicts > 0 ))
