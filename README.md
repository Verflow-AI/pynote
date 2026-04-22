# pynote

> PyPI distribution: **`jupyter-pynote`** · Python import: `pynote` · Lab extension id: `pynote`

Claude-powered chat side panel for **JupyterLab 4** and **Jupyter Notebook 7**.

Open any notebook, crack open the side panel, and talk to Claude about the code. When Claude proposes changes to the notebook, type **`apply`** in chat and they're written into real cells — no dialog box, no reload, no token-pasting.

## Features

- Right-hand side panel docked into the Lab shell; follows the currently active notebook.
- Chat with Claude about the current notebook's cells (their source is sent as context each turn).
- Structured cell edits via Claude tool-use — replace existing cells or insert new ones by stable cell id, not brittle index.
- `apply` / `cancel` are typed in chat; no modal or popup.
- Edits go through Lab's own shared model, so undo / autosave / RTC all Just Work.
- Server extension proxies the Claude call, so `ANTHROPIC_API_KEY` lives in the Jupyter process — never in the browser.

## Prerequisites

- Python 3.9+
- JupyterLab 4 or Notebook 7 (`pip install jupyterlab`)
- Node 18+ and `jlpm` (ships with JupyterLab)
- An Anthropic API key

## Install alongside your existing Jupyter

From `jupyter-pynote/`:

```bash
# 1. Install the Python side (server extension) in editable mode
pip install -e ".[dev]"

# 2. Install npm deps and build the labextension assets
jlpm install
jlpm build

# 3. Wire the labextension into JupyterLab
jupyter labextension develop . --overwrite

# 4. Enable the Jupyter server extension
jupyter server extension enable pynote

# 5. Provide your API key (or put it in a .env you source before launching)
export ANTHROPIC_API_KEY=sk-ant-...

# 6. Launch Jupyter
jupyter lab
```

Verify the extension is loaded:

```bash
jupyter labextension list      # should show: pynote v0.1.0 enabled ok
jupyter server extension list  # should show: pynote enabled
```

Open any `.ipynb`. You'll see a **pynote** tab in the right sidebar.

### Model / tokens

Override via env vars before launch:

```bash
export PYNOTE_MODEL=claude-sonnet-4-6     # default
export PYNOTE_MAX_TOKENS=4096             # default
```

## How the chat works

1. You type a question — "plot the last column" or "explain cell 3". pynote sends your message **plus a snapshot of every cell's id, type, and source** to the server extension.
2. The server forwards it to Claude with a system prompt that describes the `propose_notebook_changes` tool.
3. Claude replies with prose, and optionally calls the tool with a list of changes `{op, target_cell_id, source}`.
4. The panel shows the prose + a compact preview of each proposed change.
5. You type `apply` → pynote walks the change list and calls `sharedModel.setSource(...)` / `sharedModel.insertCell(...)` inside a single transaction. One undo reverts the whole batch.
6. Type `cancel` / `discard` / `no` to drop the proposal, or just keep chatting — a follow-up question clears the pending proposal automatically.

There's no apply button, no modal, no popup — everything is in the chat line.

## Smoke test without Lab

Quickly verify Claude integration without running Jupyter:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/smoke_test.py
```

Expected: a proposal with at least one `replace` or `insert_after` change targeting the empty cell.

## Dev workflow

```bash
# In one terminal — rebuild on TS changes
jlpm watch

# In another — Lab picks up the changes on refresh
jupyter lab
```

On Python-side changes, restart Lab.

## Uninstall

```bash
jupyter server extension disable pynote
jupyter labextension uninstall pynote
pip uninstall jupyter-pynote
```

## Troubleshooting

- **Panel doesn't appear:** run `jupyter labextension list`; if `pynote` isn't there, redo step 3.
- **Panel says "No notebook open":** that's literal — open a `.ipynb` in the same Lab window.
- **`ANTHROPIC_API_KEY is not set`:** the server process (the one running `jupyter lab`) didn't inherit the env var. Export it *in that shell* before launch.
- **`403 / xsrf` in browser console:** shouldn't happen since requests go through `@jupyterlab/services` — but if you see one, disable any other extension that proxies Lab API calls.

## License

MIT — see `LICENSE`.
