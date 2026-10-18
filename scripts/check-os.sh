#!/usr/bin/env bash
# Checks that the operating system and architecture are supported.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=scripts/lib.sh
. scripts/lib.sh

os="$(uname -s)"; arch="$(uname -m)"
case "$arch" in
  x86_64|amd64) arch_label=amd64 ;;
  aarch64|arm64) arch_label=arm64 ;;
  *) arch_label="" ;;
esac

supported=1
case "$os" in
  Linux)
    if [ -r /etc/os-release ]; then
      # shellcheck disable=SC1091
      . /etc/os-release
      label="${PRETTY_NAME:-$ID $VERSION_ID}"
      if [ "${ID:-}" != "ubuntu" ] || [[ " $SUPPORTED_UBUNTU " != *" ${VERSION_ID:-} "* ]]; then
        supported=0
      fi
    else
      label="Linux (sem /etc/os-release)"; supported=0
    fi
    ;;
  Darwin) label="macOS $(sw_vers -productVersion 2>/dev/null || echo '?')" ;;
  *) label="$os"; supported=0 ;;
esac
[ -z "$arch_label" ] && supported=0

if [ "$supported" = 1 ]; then
  ok "Sistema suportado: $label ($arch_label)"
  info "Consulte: $(requirements_file)"
  exit 0
fi

msg="Sistema não suportado: $label ($arch). Suportados: Ubuntu ${SUPPORTED_UBUNTU// /, } e macOS, em amd64 ou arm64."
if [ "${SKIP_OS_CHECK:-0}" = "1" ]; then
  warn "$msg"
  warn "SKIP_OS_CHECK=1: seguindo por sua conta e risco."
  exit 0
fi
err "$msg"
hint "Veja REQUIREMENTS.md. Para tentar mesmo assim: SKIP_OS_CHECK=1 make <alvo>"
exit 1
