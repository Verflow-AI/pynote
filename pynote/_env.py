"""Tiny zero-dependency .env loader.

We call this at package import time so both the server extension (when Jupyter
boots it) and the smoke scripts get the user's ANTHROPIC_API_KEY without
requiring them to remember `set -a; source .env; set +a`.

Uses os.environ.setdefault so a real shell export always wins over the file.
"""

from __future__ import annotations

import os
from pathlib import Path


def _candidate_paths() -> list[Path]:
    here = Path(__file__).resolve().parent
    home = Path.home()
    return [
        # User-scope config — the officially-recommended place for a key on
        # an installed (pip-installed) pynote. Never in the repo, never in
        # the wheel.
        home / ".pynote" / ".env",
        home / ".pynote.env",
        # Dev convenience — repo root when running from a source checkout.
        Path.cwd() / ".env",
        here.parent / ".env",
        here / ".env",  # defensive: inside the package (should never exist)
    ]


def load_dotenv_if_present() -> Path | None:
    """Load the first .env found; return the path that won, or None."""
    for path in _candidate_paths():
        if path.is_file():
            _apply(path)
            return path
    return None


def _apply(path: Path) -> None:
    try:
        text = path.read_text()
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip optional surrounding quotes — matches dotenv conventions.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if not key:
            continue
        os.environ.setdefault(key, value)
