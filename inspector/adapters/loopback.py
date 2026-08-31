"""Local loopback capture; it cannot bind to a public interface."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .mock import MockTarget


class LoopbackMockServer:
    capabilities = {"requests": True, "responses": True, "events": False, "streaming": False, "websockets": False, "truncated_bodies": False}

    def __init__(self, target: MockTarget | None = None, max_body_bytes: int = 1024 * 1024):
        self.target = target or MockTarget()
        self.max_body_bytes = max_body_bytes
        self.captured: list[dict[str, Any]] = []
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "LoopbackMockServer":
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
                length = int(self.headers.get("content-length", "0"))
                if length > owner.max_body_bytes:
                    self.send_error(413, "body exceeds limit")
                    return
                raw = self.rfile.read(length)
                try:
                    body = json.loads(raw.decode("utf-8")) if raw else {}
                except json.JSONDecodeError:
                    self.send_error(400, "invalid JSON")
                    return
                request = {"body": {"mode": "inline", "encoding": "json", "value": body}, "meta": {"model_requested": body.get("model") if isinstance(body, dict) else None}}
                response = owner.target.handle(request)
                response_bytes = json.dumps(response["body"], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                owner.captured.append({"request": request, "response": response})
                self.send_response(int(response["status"]))
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response_bytes)))
                self.end_headers()
                self.wfile.write(response_bytes)

            def log_message(self, *_args: Any) -> None:
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, name="inspector-loopback", daemon=True)
        self._thread.start()
        return self

    @property
    def url(self) -> str:
        if self._server is None:
            raise RuntimeError("loopback server is not running")
        return f"http://127.0.0.1:{self._server.server_port}/mock"

    def __exit__(self, *_args: Any) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._server = None
        self._thread = None
