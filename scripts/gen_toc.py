"""Insert or refresh the table of contents (TOC) at the top of every Markdown file.

The TOC goes right after the first H1 title, between the markers below, and lists the
H2 and H3 headings with GitHub-compatible anchors. Files under dados/ are never touched.

Usage:
    uv run python scripts/gen_toc.py           # rewrite the TOCs
    uv run python scripts/gen_toc.py --check   # exit 1 if any TOC is missing or outdated
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- TOC -->"
END = "<!-- /TOC -->"
TITLE = "**Sumário**"
EXCLUDED_DIRS = ("dados/", ".venv/", "node_modules/")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


def markdown_files() -> list[Path]:
    """Markdown files tracked or not ignored by git, excluding protected directories."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        out = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*.md")]
    return sorted(ROOT / f for f in out if not f.startswith(EXCLUDED_DIRS))


def slugify(text: str) -> str:
    """GitHub heading anchor: lowercase, drop punctuation, spaces become hyphens."""
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    kept = []
    for char in text:
        category = unicodedata.category(char)
        if char in " -_" or category[0] in ("L", "N") or category == "Mn":
            kept.append(char)
    return "".join(kept).replace(" ", "-")


def strip_toc(lines: list[str]) -> list[str]:
    if START in lines and END in lines:
        start, end = lines.index(START), lines.index(END)
        del lines[start : end + 1]
        while start < len(lines) and start > 0 and lines[start] == "" and lines[start - 1] == "":
            del lines[start]
    return lines


def headings(lines: list[str]) -> list[tuple[int, str]]:
    found, in_code = [], False
    for line in lines:
        if FENCE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        match = HEADING.match(line)
        if match:
            found.append((len(match.group(1)), match.group(2)))
    return found


def build_toc(lines: list[str]) -> list[str]:
    entries, seen = [], {}
    for level, text in headings(lines):
        base = slugify(text)
        count = seen.get(base, 0)
        seen[base] = count + 1
        if level not in (2, 3):
            continue
        anchor = base if count == 0 else f"{base}-{count}"
        label = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
        label = label.replace("[", "\\[").replace("]", "\\]")
        entries.append(f"{'  ' * (level - 2)}- [{label}](#{anchor})")
    if not entries:
        return []
    return [START, TITLE, "", *entries, END]


def render(text: str) -> str:
    lines = strip_toc(text.splitlines())
    toc = build_toc(lines)
    if not toc:
        return "\n".join(lines) + "\n"
    title = next(
        (i for i, line in enumerate(lines) if HEADING.match(line) and line.startswith("# ")), None
    )
    insert_at = 0 if title is None else title + 1
    block = ([""] if insert_at else []) + toc + [""]
    rest = lines[insert_at:]
    while rest and rest[0] == "":
        rest.pop(0)
    return "\n".join(lines[:insert_at] + block + rest) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only report outdated files")
    args = parser.parse_args()
    outdated = []
    for path in markdown_files():
        original = path.read_text(encoding="utf-8")
        updated = render(original)
        if updated != original:
            outdated.append(path.relative_to(ROOT))
            if not args.check:
                path.write_text(updated, encoding="utf-8")
    if args.check and outdated:
        print("[ERRO] Sumário (TOC) ausente ou desatualizado em:", file=sys.stderr)
        for path in outdated:
            print(f"       - {path}", file=sys.stderr)
        print("       ↳ Rode: make toc", file=sys.stderr)
        return 1
    for path in outdated:
        print(f"[ OK ] TOC atualizado: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
