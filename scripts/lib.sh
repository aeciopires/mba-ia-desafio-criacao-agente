#!/usr/bin/env bash
# Shared helpers for the Makefile scripts: colored, actionable messages.

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_RED=$'\033[31m'; C_GRN=$'\033[32m'; C_YEL=$'\033[33m'; C_BLU=$'\033[34m'; C_RST=$'\033[0m'
else
  C_RED=""; C_GRN=""; C_YEL=""; C_BLU=""; C_RST=""
fi

info() { printf '%s[INFO]%s %s\n' "$C_BLU" "$C_RST" "$*"; }
ok()   { printf '%s[ OK ]%s %s\n' "$C_GRN" "$C_RST" "$*"; }
warn() { printf '%s[WARN]%s %s\n' "$C_YEL" "$C_RST" "$*" >&2; }
err()  { printf '%s[ERRO]%s %s\n' "$C_RED" "$C_RST" "$*" >&2; }
hint() { printf '       %s↳ %s%s\n' "$C_YEL" "$*" "$C_RST" >&2; }

SUPPORTED_UBUNTU="${SUPPORTED_UBUNTU:-22.04 24.04 26.04}"

# Prints the requirements file for the detected system (empty if unsupported).
requirements_file() {
  case "$(uname -s)" in
    Darwin) echo "docs/requirements/REQUIREMENTS-macos.md" ;;
    Linux)
      if [ -r /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        for v in $SUPPORTED_UBUNTU; do
          if [ "${ID:-}" = "ubuntu" ] && [ "${VERSION_ID:-}" = "$v" ]; then
            echo "docs/requirements/REQUIREMENTS-ubuntu-$v.md"
            return
          fi
        done
      fi
      ;;
  esac
}
