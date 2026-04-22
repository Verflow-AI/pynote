# CLAUDE.md — guidance for agents working on this repo

This is a **JupyterLab 4 / Notebook 7 extension** that adds a Claude-powered chat side panel. Frontend is TypeScript+React mounted as a Lumino widget via `ReactWidget`. Backend is a Jupyter Server extension (Python) that proxies to the Anthropic API.

## Repo shape

```
pynote/                 Python package — server extension
  __init__.py           exposes _jupyter_labextension_paths, _jupyter_server_extension_points
  handlers.py           Tornado handlers mounted at <base_url>/pynote/{chat,health}
  claude.py             Anthropic SDK wrapper (tool-use for structured cell edits)
src/                    TypeScript frontend
  index.ts              plugin registration, inserts widget into right shell area
  widget.tsx            PynotePanelWidget (ReactWidget subclass)
  ChatPanel.tsx         the chat UI
  notebookOps.ts        INotebookTracker helpers — snapshot cells, apply changes
  api.ts                ServerConnection-based fetch to /pynote/*
  types.ts              shared request/response types
style/index.css         scoped with .pynote- prefix, uses JupyterLab CSS variables
schema/plugin.json      (reserved for future settings)
scripts/smoke_test.py   hits real Claude API with a fake notebook — no Lab needed
```

## Non-obvious invariants

- **Cells are identified by stable `id`, not by index.** `notebookOps.findCellIndexById` is the only place that converts id → index, and it does so at apply time. Never persist or emit indices.
- **All cell mutations go inside a single `sharedModel.transact(...)`** so one undo reverts the whole batch. See `applyChanges` in `notebookOps.ts`.
- **Do not add Ajax / XSRF / token-paste code.** All requests go through `ServerConnection.makeRequest`, which handles Jupyter's auth and XSRF automatically. The older sibling repo `jupyter-chatbot` has XSRF hacks because it's a Chrome extension — that code is not a reference here.
- **`ANTHROPIC_API_KEY` lives only in the server process.** Never expose it to the frontend; never put it in `schema/plugin.json`.
- **Claude is forbidden from applying changes itself.** The system prompt in `pynote/claude.py` states this. The UI then gates apply behind the user typing `apply` — do not short-circuit the gate.

## Common tasks

### Change the Claude model or system prompt

`pynote/claude.py` — `DEFAULT_MODEL`, `SYSTEM_PROMPT`, `TOOL_DEFINITION`. Restart the Jupyter process after editing (server extension is loaded once at launch).

### Add a new server route

Add a Tornado handler class to `pynote/handlers.py`, register it in `setup_handlers(web_app)`. Client-side, add a wrapper in `src/api.ts`. Always inherit from `jupyter_server.base.handlers.APIHandler` and decorate handlers with `@tornado.web.authenticated`.

### Add a new chat UX feature (e.g. slash commands)

Handled entirely in `src/ChatPanel.tsx::handleSend`. Look at the `APPLY_PHRASES` / `DISCARD_PHRASES` pattern for the current in-chat command approach. Keep commands local — don't round-trip them to Claude.

### Change how a proposed change is applied

`src/notebookOps.ts::applyChanges`. Current ops: `replace`, `insert_after`. If you add a new op (e.g. `delete`, `move`), also extend the `propose_notebook_changes` tool schema in `pynote/claude.py` and the `ChangeOp` type in `src/types.ts`.

## Build / test

```bash
jlpm install
jlpm build                                  # produces pynote/labextension/
pip install -e ".[dev]"
jupyter labextension develop . --overwrite  # wires the built assets into Lab
jupyter server extension enable pynote
jupyter lab
```

Iterate:

```bash
jlpm watch      # rebuild on TS save
# refresh the Lab browser tab to pick up frontend changes
# restart jupyter lab to pick up Python changes
```

Smoke test the backend without Lab:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/smoke_test.py
```

## Things NOT to do

- Do not introduce a Jupyter Server REST PUT to `/api/contents/...` to save notebook changes. We use the shared model in-process. Going through REST would bypass autosave and RTC.
- Do not add a confirmation dialog / modal. The product spec is explicitly "no dialog — everything in chat."
- Do not serialize cell outputs into the Claude context. Only `id`, `cell_type`, and `source` go over the wire. Outputs can balloon token usage and leak sensitive data.
- Do not bundle the Anthropic SDK into the webpack frontend. Only the server extension imports `anthropic`.
- Do not stop using tool-use for structured edits. Regexing code fences (the legacy path from `jupyter-chatbot-server`) produced silent corruption on edge cases — the tool schema is load-bearing here.

## Related repos (context only, do not edit from here)

- `../jupyter-chatbot/` — legacy Chrome extension, superseded by this repo.
- `../jupyter-chatbot-server/` — legacy FastAPI backend, superseded by `pynote/handlers.py` + `pynote/claude.py`.
