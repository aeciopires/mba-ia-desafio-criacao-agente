"""Repository consistency: version, docs pointers, requirements files and data integrity."""

from __future__ import annotations

import json
import re
import subprocess
import sys

import pytest

import aurora
from aurora.config import PROJECT_ROOT

ROOT = PROJECT_ROOT
SUPPORTED_UBUNTU = ("22.04", "24.04", "26.04")


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_version_single_source():
    version = _read("VERSION").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    assert aurora.__version__ == version
    released = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", _read("CHANGELOG.md"), re.MULTILINE)
    assert released and released[0] == version


def test_makefile_reads_version_file():
    makefile = _read("Makefile")
    assert "VERSION := $(shell cat VERSION" in makefile
    assert version_not_hardcoded(makefile)


def version_not_hardcoded(text: str) -> bool:
    return _read("VERSION").strip() not in text


def test_requirements_file_per_supported_os():
    generic = _read("REQUIREMENTS.md")
    files = [f"docs/requirements/REQUIREMENTS-ubuntu-{v}.md" for v in SUPPORTED_UBUNTU]
    files.append("docs/requirements/REQUIREMENTS-macos.md")
    for path in files:
        assert (ROOT / path).is_file(), path
        assert path in generic, f"{path} missing from REQUIREMENTS.md"
    assert f"SUPPORTED_UBUNTU := {' '.join(SUPPORTED_UBUNTU)}" in _read("Makefile")


def test_readme_code_links_exist():
    """Every `path#Lnn` link in README points to an existing file and line."""
    readme = _read("README.md")
    links = re.findall(r"\]\(((?:src|docker-compose)[^)#]*)#L(\d+)\)", readme)
    assert len(links) >= 15
    for path, line in links:
        file = ROOT / path
        assert file.is_file(), path
        assert int(line) <= len(file.read_text(encoding="utf-8").splitlines()), f"{path}#L{line}"


@pytest.mark.parametrize(
    ("path", "line", "snippet"),
    [
        ("src/aurora/tools/reservas.py", 101, "request_confirmation("),
        ("src/aurora/tools/visitantes.py", 48, "request_confirmation("),
        ("src/aurora/runtime.py", 155, "user_id=apartamento"),
        ("src/aurora/runtime.py", 235, "ConfirmationNotPendingError"),
        ("src/aurora/runtime.py", 131, "DatabaseSessionService("),
        ("src/aurora/runtime.py", 138, "ResumabilityConfig("),
        ("src/aurora/agents/__init__.py", 96, "AgentTool("),
        ("src/aurora/db/schema.sql", 27, "ux_reserva_ativa"),
        ("src/aurora/db/repository.py", 117, "BEGIN IMMEDIATE"),
        ("src/aurora/db/repository.py", 254, "indisponivel"),
        ("src/aurora/db/repository.py", 269, "apartamento = ?"),
        ("docker-compose.yml", 27, "./var:/app/var"),
    ],
)
def test_readme_guarantee_pointers_match_code(path, line, snippet):
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    assert snippet in lines[line - 1], f"{path}:{line} no longer contains {snippet!r}"
    assert f"{path}#L{line}" in _read("README.md")


def test_openapi_snapshot_is_current(settings):
    from aurora.api.main import create_app

    current = create_app(settings).openapi()
    saved = json.loads(_read("docs/openapi.json"))
    assert saved == current, "docs/openapi.json is outdated: run `make openapi`"


def test_env_example_has_names_only():
    for line in _read(".env.example").splitlines():
        if line and not line.startswith("#"):
            name, _, value = line.partition("=")
            assert value == "", f"{name} must not have a value in .env.example"


def test_data_files_untouched():
    result = subprocess.run(
        ["git", "diff", "--stat", "HEAD", "--", "dados/"], cwd=ROOT, capture_output=True, text=True
    )
    if result.returncode != 0:
        pytest.skip("git not available")
    assert result.stdout.strip() == ""


def test_adk_version_pinned():
    pyproject = _read("pyproject.toml")
    match = re.search(r'"google-adk\[db\]==(\d+)\.(\d+)\.(\d+)"', pyproject)
    assert match, "google-adk must be pinned to an exact version"
    major, minor, _ = map(int, match.groups())
    assert major == 2 and minor >= 2


def test_markdown_tocs_are_current():
    result = subprocess.run(
        [sys.executable, "scripts/gen_toc.py", "--check"], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_visual_guide_has_diagrams_and_analogies():
    guide = _read("docs/guia-visual.md")
    assert guide.count("```mermaid") >= 15
    assert guide.count("**Analogia:**") >= 10
    for kind in ("flowchart", "sequenceDiagram", "classDiagram", "erDiagram", "stateDiagram-v2"):
        assert kind in guide, kind
    assert "```mermaid" in _read("README.md")
    assert "docs/guia-visual.md" in _read("README.md")
