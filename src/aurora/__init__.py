"""Residencial Aurora virtual assistant."""

from importlib import metadata
from pathlib import Path

_VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION"


def _read_version() -> str:
    """Return the project version, using the VERSION file as the single source of truth."""
    if _VERSION_FILE.is_file():
        return _VERSION_FILE.read_text(encoding="utf-8").strip()
    try:
        return metadata.version("aurora")
    except metadata.PackageNotFoundError:
        return "0.0.0+unknown"


__version__ = _read_version()
