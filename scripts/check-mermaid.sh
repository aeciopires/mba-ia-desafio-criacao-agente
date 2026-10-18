#!/usr/bin/env bash
# Validates every ```mermaid block in the Markdown files by rendering it with the
# official mermaid-cli Docker image. Reports file, block number and parser error.
set -uo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=scripts/lib.sh
. scripts/lib.sh

IMAGE="${MERMAID_IMAGE:-minlag/mermaid-cli:11.17.0}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

command -v docker >/dev/null 2>&1 || { err "docker não encontrado (necessário para validar os diagramas)."; hint "make check-dependencies"; exit 1; }

python3 - "$work" <<'PY'
import pathlib, re, subprocess, sys
out = pathlib.Path(sys.argv[1])
files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
                       capture_output=True, text=True).stdout.split()
index = []
for f in files:
    if f.startswith("dados/"):
        continue
    text = pathlib.Path(f).read_text(encoding="utf-8")
    for n, block in enumerate(re.findall(r"```mermaid\n(.*?)```", text, re.S), 1):
        name = f"{len(index):03d}.mmd"
        (out / name).write_text(block, encoding="utf-8")
        index.append(f"{name}\t{f}\t{n}")
(out / "index.tsv").write_text("\n".join(index) + "\n", encoding="utf-8")
PY

total=0; failed=0
while IFS=$'\t' read -r name file n; do
  [ -z "$name" ] && continue
  total=$((total + 1))
  if ! docker run --rm -u "$(id -u):$(id -g)" -v "$work:/data" "$IMAGE" \
      -i "/data/$name" -o "/data/${name%.mmd}.svg" >/dev/null 2>"$work/${name%.mmd}.err"; then
    failed=$((failed + 1))
    err "Diagrama inválido: $file (bloco mermaid nº $n)"
    grep -m3 -E "Error|Parse|Expecting" "$work/${name%.mmd}.err" | sed 's/^/       /' >&2
  fi
done < "$work/index.tsv"

if [ "$failed" -gt 0 ]; then
  err "$failed de $total diagramas com erro."
  hint "Teste o trecho em https://mermaid.live e use rótulos entre aspas quando tiverem símbolos."
  exit 1
fi
ok "$total diagramas Mermaid válidos."
