"""Thin Claude wrapper. Uses tool-use so the model emits structured cell edits
the frontend can apply verbatim — no regex-parsing of code fences."""

from __future__ import annotations

import os
from typing import Any

try:
    from anthropic import Anthropic
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "pynote requires the `anthropic` package. Install with `pip install anthropic`."
    ) from exc


DEFAULT_MODEL = os.environ.get("PYNOTE_MODEL", "claude-sonnet-4-6")
DEFAULT_MAX_TOKENS = int(os.environ.get("PYNOTE_MAX_TOKENS", "4096"))


SYSTEM_PROMPT = """You are pynote, an AI pair-programmer embedded in a JupyterLab side panel.

You see the user's current notebook as a list of cells, each with an `id`, `cell_type`, and `source`. When the user asks for code, explanations, or fixes:

1. Discuss what you plan to do in plain prose first.
2. If and only if the user asks you to write or modify code, call the `propose_notebook_changes` tool with the concrete cell operations. Do NOT also paste the same code inside triple backticks in your text — the tool call IS the patch.
3. If the user just wants to talk through an approach, answer in prose without calling the tool.

Rules for the tool call:
- Use `replace` with a `target_cell_id` to overwrite an existing cell's source.
- Use `insert_after` with a `target_cell_id` (or no target for "append to end") to add a new cell.
- Keep each cell short and runnable — one concept per cell.
- Match the existing notebook style (imports at top, etc.).

After you propose changes, the user can type `apply` in chat to accept them, or continue the conversation to iterate. You never apply changes yourself."""


TOOL_DEFINITION: dict[str, Any] = {
    "name": "propose_notebook_changes",
    "description": "Propose one or more edits to the user's notebook. The user must confirm before they take effect.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "One-sentence summary of the proposed changes, shown to the user.",
            },
            "changes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "op": {
                            "type": "string",
                            "enum": ["replace", "insert_after"],
                        },
                        "target_cell_id": {
                            "type": "string",
                            "description": "ID of the cell to replace or insert after. For insert_after, omit to append at end.",
                        },
                        "cell_type": {
                            "type": "string",
                            "enum": ["code", "markdown"],
                            "description": "Cell type for inserts. Default: code.",
                        },
                        "source": {
                            "type": "string",
                            "description": "Full cell source (not a diff).",
                        },
                    },
                    "required": ["op", "source"],
                },
            },
        },
        "required": ["summary", "changes"],
    },
}


def _format_cells(cells: list[dict]) -> str:
    if not cells:
        return "(the notebook is empty)"
    lines = []
    for i, c in enumerate(cells):
        src = c.get("source", "")
        if isinstance(src, list):
            src = "".join(src)
        cid = c.get("id", f"<no-id-{i}>")
        ctype = c.get("cell_type", "code")
        lines.append(f"--- cell[{i}] id={cid} type={ctype} ---\n{src}")
    return "\n".join(lines)


def chat(
    messages: list[dict],
    cells: list[dict],
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> dict:
    """Send a chat turn to Claude.

    Returns {"text": str, "proposal": dict | None}. `proposal` is the raw
    `propose_notebook_changes` tool input when Claude decides to edit.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Export it before starting Jupyter."
        )

    client = Anthropic()

    notebook_context = {
        "role": "user",
        "content": f"Current notebook state:\n\n{_format_cells(cells)}",
    }
    all_messages = [notebook_context] + messages

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        tools=[TOOL_DEFINITION],
        messages=all_messages,
    )

    text_parts: list[str] = []
    proposal: dict | None = None

    for block in response.content:
        btype = getattr(block, "type", None)
        if btype == "text":
            text_parts.append(block.text)
        elif btype == "tool_use" and block.name == "propose_notebook_changes":
            proposal = dict(block.input)

    return {
        "text": "\n\n".join(text_parts).strip() or "(no reply)",
        "proposal": proposal,
        "stop_reason": response.stop_reason,
    }
