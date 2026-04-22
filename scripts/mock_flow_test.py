"""Mock-Claude integration test — verifies the claude.chat() contract and
the handler wiring without needing a real ANTHROPIC_API_KEY."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-fake")

from pynote import claude  # noqa: E402


class FakeBlock:
    def __init__(self, btype, text=None, name=None, tool_input=None):
        self.type = btype
        self.text = text
        self.name = name
        self.input = tool_input


class FakeResponse:
    def __init__(self, content, stop_reason="tool_use"):
        self.content = content
        self.stop_reason = stop_reason


def test_text_only_reply():
    fake_client = MagicMock()
    fake_client.messages.create.return_value = FakeResponse(
        content=[FakeBlock("text", text="Sure, here's what I'd do…")],
        stop_reason="end_turn",
    )
    with patch.object(claude, "Anthropic", return_value=fake_client):
        result = claude.chat(
            messages=[{"role": "user", "content": "Explain this notebook"}],
            cells=[{"id": "c1", "cell_type": "code", "source": "print('hi')"}],
        )
    assert result["text"] == "Sure, here's what I'd do…", result
    assert result["proposal"] is None, result
    print("PASS  text-only reply")


def test_tool_use_reply():
    proposal_input = {
        "summary": "Fill c-empty with a sample DataFrame.",
        "changes": [
            {
                "op": "replace",
                "target_cell_id": "c-empty",
                "cell_type": "code",
                "source": "import pandas as pd\ndf = pd.DataFrame({'a': [1,2,3]})\ndf",
            }
        ],
    }
    fake_client = MagicMock()
    fake_client.messages.create.return_value = FakeResponse(
        content=[
            FakeBlock("text", text="Filling in a DataFrame as requested."),
            FakeBlock(
                "tool_use",
                name="propose_notebook_changes",
                tool_input=proposal_input,
            ),
        ]
    )
    with patch.object(claude, "Anthropic", return_value=fake_client):
        result = claude.chat(
            messages=[{"role": "user", "content": "Fill c-empty with a sample DF"}],
            cells=[
                {"id": "c-empty", "cell_type": "code", "source": ""},
            ],
        )
    assert result["text"] == "Filling in a DataFrame as requested.", result
    assert result["proposal"] == proposal_input, result
    assert result["proposal"]["changes"][0]["op"] == "replace"
    assert "pandas" in result["proposal"]["changes"][0]["source"]
    print("PASS  tool-use reply — proposal parsed")


def test_request_shape_sent_to_claude():
    """Makes sure the notebook snapshot is injected as the first user turn."""
    captured = {}

    def capture_create(**kwargs):
        captured.update(kwargs)
        return FakeResponse(content=[FakeBlock("text", text="ok")], stop_reason="end_turn")

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = capture_create
    with patch.object(claude, "Anthropic", return_value=fake_client):
        claude.chat(
            messages=[{"role": "user", "content": "hi"}],
            cells=[{"id": "c1", "cell_type": "code", "source": "x = 1"}],
        )
    msgs = captured["messages"]
    assert msgs[0]["role"] == "user"
    assert "cell[0] id=c1" in msgs[0]["content"]
    assert "x = 1" in msgs[0]["content"]
    assert msgs[1] == {"role": "user", "content": "hi"}
    assert captured["tools"][0]["name"] == "propose_notebook_changes"
    assert "pynote" in captured["system"]
    print("PASS  request shape — notebook snapshot prepended, tool registered, system prompt present")


if __name__ == "__main__":
    test_text_only_reply()
    test_tool_use_reply()
    test_request_shape_sent_to_claude()
    print("\nAll backend flow checks passed.")
