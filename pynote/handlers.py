"""Tornado handlers for pynote's server-side routes.

Routes are mounted under `<base_url>/pynote/`. Requests are authenticated by
Jupyter Server's own auth (token or cookie) via `@tornado.web.authenticated`,
and XSRF is enforced by the server — no extra plumbing required.
"""

from __future__ import annotations

import json
import traceback

import tornado

from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join

from .claude import chat as claude_chat


class ChatHandler(APIHandler):
    @tornado.web.authenticated
    def post(self) -> None:
        try:
            body = json.loads(self.request.body or b"{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.finish(json.dumps({"error": "invalid JSON"}))
            return

        messages = body.get("messages") or []
        cells = body.get("cells") or []

        if not isinstance(messages, list) or not isinstance(cells, list):
            self.set_status(400)
            self.finish(json.dumps({"error": "messages and cells must be lists"}))
            return

        try:
            result = claude_chat(messages, cells)
        except Exception as exc:
            self.log.exception("claude_chat failed")
            self.set_status(500)
            self.finish(
                json.dumps(
                    {
                        "error": str(exc),
                        "trace": traceback.format_exc(),
                    }
                )
            )
            return

        self.finish(json.dumps(result))


class HealthHandler(APIHandler):
    @tornado.web.authenticated
    def get(self) -> None:
        import os

        self.finish(
            json.dumps(
                {
                    "ok": True,
                    "anthropic_key_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
                }
            )
        )


def setup_handlers(web_app) -> None:
    host_pattern = ".*$"
    base_url = web_app.settings["base_url"]
    handlers = [
        (url_path_join(base_url, "pynote", "chat"), ChatHandler),
        (url_path_join(base_url, "pynote", "health"), HealthHandler),
    ]
    web_app.add_handlers(host_pattern, handlers)
