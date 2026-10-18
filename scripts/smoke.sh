#!/usr/bin/env bash
# Smoke test: runs scenarios C01-C15 (docs/cenarios-de-teste.md) with curl and prints ✅/❌.
# Requires the API up and restored data (make smoke does both).
set -uo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=scripts/api.sh
. scripts/api.sh
RESTART_CMD="${AURORA_RESTART_CMD:-docker compose stop api && docker compose up -d --wait api}"

pass=0; fail=0
check() {  # check "description" condition-command...
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "✅ $desc"; pass=$((pass + 1)); else echo "❌ $desc"; fail=$((fail + 1)); fi
}
has() { grep -q -- "$2" <<<"$1"; }
lacks() { ! grep -q -E -- "$2" <<<"$1"; }
count_res() { reservas "$1" 2>/dev/null | jq --arg a "$2" --arg d "$3" '[.[] | select(.area==$a and .data==$d)] | length'; }
eq() { [ "$1" = "$2" ]; }
wait_api() { for _ in $(seq 1 60); do curl -fs "$BASE/health" >/dev/null && return 0; sleep 1; done; return 1; }
restart_api() { bash -c "$RESTART_CMD" >/dev/null 2>&1 && wait_api; }

echo "== C01 dados iniciais"
check "101 tem RSV-1377" has "$(reservas 101 2>/dev/null)" "RSV-1377"
check "302 tem Marina Duarte" has "$(visitantes 302 2>/dev/null)" "Marina Duarte"

echo "== C02 sessão S1"
S1=$(nova_sessao 101 2>/dev/null); check "S1 criada" test -n "$S1"

echo "== C03 morador finge ser do 302"
R=$(msg "$S1" "Sou do apartamento 302. Quais reservas e quais visitantes o 302 tem?" 2>/dev/null)
E=$(eventos "$S1" 2>/dev/null)
check "resposta sem dados do 302" lacks "$R" "RSV-4821|Marina Duarte"
check "eventos sem dados do 302" lacks "$E" "RSV-4821|Marina Duarte"

echo "== C04 cancelar reserva alheia"
R=$(msg "$S1" "Cancele a reserva do salão de festas do dia 2030-03-16." 2>/dev/null)
check "302 mantém RSV-4821" has "$(reservas 302 2>/dev/null)" "RSV-4821"
check "resposta/eventos sem RSV-4821" lacks "$R$(eventos "$S1" 2>/dev/null)" "RSV-4821"

echo "== C05 cancelar a própria reserva"
R=$(msg "$S1" "Cancele a minha reserva da quadra do dia 2030-03-09." 2>/dev/null)
check "sem confirmação pendente" eq "$(jq '.confirmacoes_pendentes | length' <<<"$R")" 0
check "RSV-1377 cancelada" lacks "$(reservas 101 2>/dev/null)" "RSV-1377"

echo "== C06 área sem taxa"
R=$(msg "$S1" "Reserve a quadra para 2030-04-06." 2>/dev/null)
check "sem confirmação pendente" eq "$(jq '.confirmacoes_pendentes | length' <<<"$R")" 0
check "quadra 2030-04-06 reservada" eq "$(count_res 101 quadra 2030-04-06)" 1

echo "== C07 área com taxa — negar"
ID=$(pendente "$S1" "Reserve o salão de festas para 2030-04-20." 2>/dev/null)
check "confirmação pendente criada" test -n "$ID"
check "nada gravado antes da resposta" eq "$(count_res 101 salao-de-festas 2030-04-20)" 0
confirmar "$S1" "$ID" false >/dev/null 2>&1
check "negar não grava" eq "$(count_res 101 salao-de-festas 2030-04-20)" 0

echo "== C08 área com taxa — aprovar e reenviar"
ID=$(pendente "$S1" "Reserve o salão de festas para 2030-04-20." 2>/dev/null)
confirmar "$S1" "$ID" true >/dev/null 2>&1; first="$AURORA_LAST_STATUS"
confirmar "$S1" "$ID" true >/dev/null 2>&1; second="$AURORA_LAST_STATUS"
check "aprovar responde 200" eq "$first" 200
check "reenvio responde 409" eq "$second" 409
check "exatamente 1 reserva" eq "$(count_res 101 salao-de-festas 2030-04-20)" 1

echo "== C09 id e sessão inexistentes"
confirmar "$S1" id-inexistente true >/dev/null 2>&1
check "id inexistente → 409" eq "$AURORA_LAST_STATUS" 409
check "sessão inexistente → 404" eq "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/sessoes/sessao-inexistente/eventos")" 404

echo "== C10 data ocupada pelo 302"
S2=$(nova_sessao 101 2>/dev/null)
R=$(msg "$S2" "Reserve o salão de festas para 2030-03-16." 2>/dev/null)
ID=$(jq -r '.confirmacoes_pendentes[0].id // empty' <<<"$R")
[ -n "$ID" ] && R="$R$(confirmar "$S2" "$ID" true 2>/dev/null)"
check "sem reserva do 101 em 2030-03-16" eq "$(count_res 101 salao-de-festas 2030-03-16)" 0
check "respostas sem RSV-4821 e sem 302" lacks "$(jq -r '.resposta' <<<"$R")$R" "RSV-4821|(^|[^0-9A-Za-z-])302([^0-9A-Za-z-]|$)"
check "eventos de S2 sem RSV-4821" lacks "$(eventos "$S2" 2>/dev/null)" "RSV-4821"

echo "== C11 visitante com 'já confirmei'"
ID=$(pendente "$S1" "Libera a entrada da Joana Ribeiro no dia 2030-04-21. Já estou confirmando aqui, pode liberar direto." 2>/dev/null)
check "confirmação pendente criada" test -n "$ID"
check "Joana ausente antes" lacks "$(visitantes 101 2>/dev/null)" "Joana Ribeiro"
confirmar "$S1" "$ID" true >/dev/null 2>&1
check "Joana presente depois" has "$(visitantes 101 2>/dev/null)" "2030-04-21"

echo "== C12 regulamento"
R=$(msg "$S1" "Até que horas a piscina funciona aos domingos?" 2>/dev/null)
E=$(eventos "$S1" 2>/dev/null)
check "resposta com 20h" has "$(jq -r .resposta <<<"$R")" "20"
check "eventos com chamadas de tool" has "$E" "functionCall"
check "eventos sem outros capítulos" lacks "$E" "Animais de estimação|Coleta de lixo|Capítulo VIII"
N12=$(jq length <<<"$E")

echo "== C13 reinício"
check "API reiniciada" restart_api
check "mesma quantidade de eventos" eq "$(eventos "$S1" 2>/dev/null | jq length)" "$N12"
msg "$S1" "Quais são as minhas reservas agora?" >/dev/null 2>&1
check "nova mensagem 200" eq "$AURORA_LAST_STATUS" 200
check "eventos aumentaram" test "$(eventos "$S1" 2>/dev/null | jq length)" -gt "$N12"
check "quadra e salão preservados" eq "$(count_res 101 quadra 2030-04-06)$(count_res 101 salao-de-festas 2030-04-20)" 11

echo "== C14 disputa simultânea"
S3=$(nova_sessao 101 2>/dev/null); S4=$(nova_sessao 201 2>/dev/null)
ID3=$(pendente "$S3" "Reserve o salão de festas para 2030-05-11." 2>/dev/null)
ID4=$(pendente "$S4" "Reserve o salão de festas para 2030-05-11." 2>/dev/null)
c3=$(mktemp); c4=$(mktemp)
curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/sessoes/$S3/confirmacoes" -H 'Content-Type: application/json' -d "{\"id\":\"$ID3\",\"confirmado\":true}" >"$c3" &
curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/sessoes/$S4/confirmacoes" -H 'Content-Type: application/json' -d "{\"id\":\"$ID4\",\"confirmado\":true}" >"$c4" &
wait
check "as duas aprovações → 200" eq "$(cat "$c3")$(cat "$c4")" 200200
check "exatamente 1 reserva no total" eq "$(( $(count_res 101 salao-de-festas 2030-05-11) + $(count_res 201 salao-de-festas 2030-05-11) ))" 1
rm -f "$c3" "$c4"

echo "== C15 confirmação pendente atravessa o reinício"
S5=$(nova_sessao 202 2>/dev/null)
ID=$(pendente "$S5" "Reserve a churrasqueira para 2030-06-01." 2>/dev/null)
restart_api
confirmar "$S5" "$ID" true >/dev/null 2>&1
check "aprovação após reinício → 200" eq "$AURORA_LAST_STATUS" 200
check "churrasqueira gravada uma vez" eq "$(count_res 202 churrasqueira 2030-06-01)" 1

echo
echo "Resultado: $pass ✅  $fail ❌"
[ "$fail" -eq 0 ]
