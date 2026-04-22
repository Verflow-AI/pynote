"""pynote — Claude-powered chat side panel for JupyterLab 4 / Notebook 7."""

from ._env import load_dotenv_if_present

# Pull .env into os.environ before anything else in the package imports, so
# ANTHROPIC_API_KEY is visible to claude.py regardless of whether the user
# remembered to `source .env` in their shell.
load_dotenv_if_present()

from ._version import __version__  # noqa: E402
from .handlers import setup_handlers  # noqa: E402


def _jupyter_labextension_paths():
    return [{"src": "labextension", "dest": "pynote"}]


def _jupyter_server_extension_points():
    return [{"module": "pynote"}]


def _load_jupyter_server_extension(server_app):
    """Called by Jupyter Server when the extension loads."""
    setup_handlers(server_app.web_app)
    server_app.log.info("pynote server extension loaded")


# Backward-compat name used by older Notebook servers.
load_jupyter_server_extension = _load_jupyter_server_extension

__all__ = ["__version__"]
