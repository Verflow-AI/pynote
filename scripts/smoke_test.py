"""Offline smoke test for pynote's Claude integration.

Runs one end-to-end request against the real Claude API using a fake
notebook. Requires ANTHROPIC_API_KEY in the environment.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/smoke_test.py
"""

from __future__ import annotations

import json
import os
import sys

# Allow running from repo root without installing the package.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

# Importing the top-level pynote package triggers the .env loader.
import pynote  # noqa: F401, E402
from pynote.claude import chat  # noqa: E402


FAKE_CELLS = [
    {"id": "c-imports", "cell_type": "code", "source": "import pandas as pd\n"},
    {"id": "c-empty", "cell_type": "code", "source": ""},
]


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set — can't hit Claude.")
        return 1

    messages = [
        {
            "role": "user",
            "content": (
                "In the empty cell c-empty, create a small sample DataFrame "
                "with columns name, age, and score for three people. Keep it "
                "runnable."
            ),
        }
    ]

    result = chat(messages, FAKE_CELLS)
    print("=== TEXT ===")
    print(result["text"])
    print()
    print("=== PROPOSAL ===")
    print(json.dumps(result["proposal"], indent=2))

    proposal = result["proposal"]
    if not proposal or not proposal.get("changes"):
        print("\nFAIL: Claude did not return a tool-use proposal.")
        return 2

    # Basic sanity checks on the proposal.
    for ch in proposal["changes"]:
        assert ch["op"] in {"replace", "insert_after"}, ch
        assert isinstance(ch.get("source", ""), str), ch

    print("\nOK: proposal parsed and passed shape checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
