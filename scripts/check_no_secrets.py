"""Pre-release safety check.

Builds (or inspects) a wheel + sdist and fails loudly if any artefact
contains files or strings that look like secrets. Run before `twine upload`:

    python scripts/check_no_secrets.py dist/*.whl dist/*.tar.gz

Exits 0 on clean, non-zero on any suspicious find. No network, no mutation.
"""

from __future__ import annotations

import re
import sys
import tarfile
import zipfile
from pathlib import Path


# Patterns that should NEVER be in a published artefact.
SECRET_PATTERNS = [
    re.compile(rb"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(rb"sk-[A-Za-z0-9]{32,}"),          # generic OpenAI-style
    re.compile(rb"AIza[0-9A-Za-z_-]{35}"),         # Google API key
    re.compile(rb"AKIA[0-9A-Z]{16}"),              # AWS access key
    re.compile(rb"-----BEGIN (RSA|OPENSSH|EC) PRIVATE KEY-----"),
]

# Files that should NEVER ship in an artefact (name-based check).
BANNED_NAMES = {".env", ".envrc", ".npmrc", ".pypirc"}
BANNED_SUFFIXES = (".pem", ".key", ".p12", ".pfx")


def iter_artefact_entries(path: Path):
    """Yield (entry_name, bytes) for every file inside wheel or sdist."""
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                with zf.open(info) as fh:
                    yield info.filename, fh.read()
    elif path.name.endswith(".tar.gz") or path.suffix == ".tar":
        with tarfile.open(path) as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                fh = tf.extractfile(member)
                if fh is None:
                    continue
                yield member.name, fh.read()
    else:
        raise ValueError(f"Unknown artefact type: {path}")


def check_artefact(path: Path) -> list[str]:
    problems: list[str] = []
    for name, data in iter_artefact_entries(path):
        basename = name.rsplit("/", 1)[-1]
        if basename in BANNED_NAMES:
            problems.append(f"[banned filename] {path.name} contains {name}")
            continue
        if any(basename.endswith(s) for s in BANNED_SUFFIXES):
            problems.append(f"[banned suffix]  {path.name} contains {name}")
            continue
        # Limit scan to reasonably small files (compiled JS can be big but
        # wouldn't plausibly contain a fresh API key unless someone typed it).
        for pattern in SECRET_PATTERNS:
            m = pattern.search(data)
            if m:
                snippet = m.group(0)[:12].decode(errors="replace")
                problems.append(
                    f"[secret pattern] {path.name}:{name} matches {pattern.pattern!r} "
                    f"(starts with {snippet}…)"
                )
    return problems


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: check_no_secrets.py <artefact> [artefact ...]", file=sys.stderr)
        return 2

    all_problems: list[str] = []
    for arg in argv[1:]:
        path = Path(arg)
        if not path.is_file():
            print(f"[error] not a file: {path}", file=sys.stderr)
            all_problems.append(f"missing: {path}")
            continue
        problems = check_artefact(path)
        if problems:
            all_problems.extend(problems)
            print(f"[FAIL] {path}:")
            for p in problems:
                print("  ", p)
        else:
            print(f"[ok]   {path}")

    if all_problems:
        print(f"\n{len(all_problems)} problem(s) — do NOT upload these artefacts.", file=sys.stderr)
        return 1
    print("\nAll artefacts clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
