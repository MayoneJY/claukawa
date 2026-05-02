from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any

from PySide6.QtCore import QObject, Signal

from . import GATEWAY_HOST, GATEWAY_PORT

_log = logging.getLogger(__name__)


class GatewaySignals(QObject):
    eventReceived = Signal(dict)


class _Handler(BaseHTTPRequestHandler):
    signals: GatewaySignals  # set by Gateway.start()

    def log_message(self, format: str, *args: Any) -> None:
        _log.debug("gateway " + format, *args)

    def _respond(self, code: int, body: bytes = b"", content_type: str = "text/plain") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._respond(200, b"ok")
            return
        self._respond(404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/event":
            self._respond(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._respond(400, b"invalid json")
            return
        if not isinstance(payload, dict):
            self._respond(400, b"json root must be object")
            return
        try:
            self.signals.eventReceived.emit(payload)
        except Exception:  # pragma: no cover
            _log.exception("failed to emit event signal")
        self._respond(204)


class Gateway:
    def __init__(self) -> None:
        self.signals = GatewaySignals()
        self._server: ThreadingHTTPServer | None = None
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._server is not None:
            return
        handler_cls = type("Handler", (_Handler,), {"signals": self.signals})
        self._server = ThreadingHTTPServer((GATEWAY_HOST, GATEWAY_PORT), handler_cls)
        self._thread = Thread(
            target=self._server.serve_forever,
            name="claukawa-gateway",
            daemon=True,
        )
        self._thread.start()
        _log.info("gateway listening on http://%s:%d", GATEWAY_HOST, GATEWAY_PORT)

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None
