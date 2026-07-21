"""Dependency-free HTTP server for the local Acheon demo."""

from __future__ import annotations

import hmac
import json
import mimetypes
import os
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .compiler import ContextBudgetError, ContextCompiler
from .demo import DEMO_NAMESPACE, seed_demo
from .models import CompileConfig
from .runtime import (
    DEFAULT_MODEL,
    AcheonRuntime,
    OpenAIResponsesAdapter,
    ResponsesClient,
    RuntimeCallError,
    RuntimeUnavailableError,
)
from .selector import ProtectedSelectionError
from .store import MemoryStore, StoreConflict, StoreCorruption

MAX_REQUEST_BYTES = 1_048_576
WEB_ROOT = Path(__file__).with_name("web")
STATIC_ROUTES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/app.js": "app.js",
    "/styles.css": "styles.css",
}


class RequestError(ValueError):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        super().__init__(message)
        self.status = status


def _as_namespace(value: Any) -> str:
    namespace = str(value if value is not None else DEMO_NAMESPACE).strip()
    if not namespace or len(namespace) > 128:
        raise RequestError("namespace must be 1..128 characters")
    return namespace


def _as_query(value: Any) -> str:
    query = str(value if value is not None else "").strip()
    if not query:
        raise RequestError("query is required")
    if len(query) > 20_000:
        raise RequestError("query is too long")
    return query


def _as_scopes(value: Any) -> tuple[str, ...]:
    if value is None:
        return ("global",)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RequestError("scopes must be an array of strings")
    scopes = tuple(item.strip() for item in value if item.strip())
    if len(scopes) > 32 or any(len(item) > 128 for item in scopes):
        raise RequestError("scopes exceed the supported size")
    return scopes or ("global",)


def _as_budget(value: Any) -> int:
    if value is None:
        return 800
    if isinstance(value, bool):
        raise RequestError("budget_tokens must be an integer")
    try:
        budget = int(value)
    except (TypeError, ValueError) as exc:
        raise RequestError("budget_tokens must be an integer") from exc
    if not 160 <= budget <= 100_000:
        raise RequestError("budget_tokens must be between 160 and 100000")
    return budget


def _as_preview(value: Any) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise RequestError("preview must be a boolean")
    return value


@dataclass(slots=True)
class AcheonApplication:
    """Long-lived store and injectable provider boundary used by the HTTP server."""

    store: MemoryStore
    adapter: OpenAIResponsesAdapter
    auth_token: str | None = None
    live_http_enabled: bool = False
    _health_cache: tuple[float, bool] | None = field(
        default=None,
        init=False,
        repr=False,
    )

    @classmethod
    def create(
        cls,
        *,
        db_path: str | Path,
        client: ResponsesClient | None = None,
        model: str | None = None,
        auth_token: str | None = None,
        enable_live_http: bool = False,
    ) -> AcheonApplication:
        return cls(
            store=MemoryStore(db_path),
            adapter=OpenAIResponsesAdapter(
                client=client,
                model=model,
                force_preview=not enable_live_http,
            ),
            auth_token=auth_token,
            live_http_enabled=enable_live_http,
        )

    def close(self) -> None:
        self.store.close()

    def health(self) -> dict[str, Any]:
        preview_only = self.adapter.preview_only
        now = time.monotonic()
        if self._health_cache is None or now - self._health_cache[0] > 5.0:
            self._health_cache = (now, self.store.verify_audit())
        audit_valid = self._health_cache[1]
        return {
            "status": "ok" if audit_valid else "degraded",
            "service": "acheon",
            "mode": "preview_only" if preview_only else "online_ready",
            "preview_only": preview_only,
            "live_http_enabled": self.live_http_enabled,
            "model": self.adapter.model,
            "audit_valid": audit_valid,
        }

    def seed(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        namespace = _as_namespace(payload.get("namespace"))
        result = seed_demo(self.store, namespace)
        result["audit_valid"] = self.store.verify_audit()
        return result

    def compile(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        query = _as_query(payload.get("query"))
        namespace = _as_namespace(payload.get("namespace"))
        scopes = _as_scopes(payload.get("scopes"))
        budget = _as_budget(payload.get("budget_tokens"))
        packet = ContextCompiler(self.store, CompileConfig(budget_tokens=budget)).compile(
            query=query, namespace=namespace, scopes=scopes
        )
        return packet.to_dict()

    def ask(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        query = _as_query(payload.get("query"))
        namespace = _as_namespace(payload.get("namespace"))
        scopes = _as_scopes(payload.get("scopes"))
        budget = _as_budget(payload.get("budget_tokens"))
        force_preview = _as_preview(payload.get("preview"))
        adapter = (
            OpenAIResponsesAdapter(model=self.adapter.model, force_preview=True)
            if force_preview
            else self.adapter
        )
        runtime = AcheonRuntime(
            self.store,
            compiler=ContextCompiler(self.store, CompileConfig(budget_tokens=budget)),
            adapter=adapter,
        )
        return runtime.ask(query, namespace=namespace, scopes=scopes).to_dict()


class AcheonHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        application: AcheonApplication,
    ) -> None:
        self.application = application
        super().__init__(server_address, AcheonRequestHandler)


class AcheonRequestHandler(BaseHTTPRequestHandler):
    server: AcheonHTTPServer
    protocol_version = "HTTP/1.1"

    def _authorized(self) -> bool:
        expected = self.server.application.auth_token
        if expected is None:
            return True
        supplied = self.headers.get("Authorization", "")
        prefix = "Bearer "
        return supplied.startswith(prefix) and hmac.compare_digest(
            supplied[len(prefix) :], expected
        )

    def _send_bytes(
        self,
        status: HTTPStatus,
        data: bytes,
        content_type: str,
        *,
        cache_control: str = "no-store",
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache_control)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self'; base-uri 'none'; "
            "form-action 'self'; frame-ancestors 'none'",
        )
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _send_json(self, status: HTTPStatus, payload: Mapping[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send_bytes(status, data, "application/json; charset=utf-8")

    def _read_json(self) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise RequestError("Content-Type must be application/json")
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise RequestError("Content-Length is required", HTTPStatus.LENGTH_REQUIRED)
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise RequestError("invalid Content-Length") from exc
        if not 0 <= length <= MAX_REQUEST_BYTES:
            raise RequestError("request body is too large", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RequestError("request body must be valid UTF-8 JSON") from exc
        if not isinstance(value, dict):
            raise RequestError("request JSON must be an object")
        return value

    def _serve_static(self) -> None:
        path = self.path.split("?", 1)[0]
        filename = STATIC_ROUTES.get(path)
        if filename is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        file_path = WEB_ROOT / filename
        try:
            data = file_path.read_bytes()
        except FileNotFoundError:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "asset_not_found"})
            return
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type == "application/javascript":
            content_type += "; charset=utf-8"
        self._send_bytes(
            HTTPStatus.OK,
            data,
            content_type,
            cache_control="public, max-age=60",
        )

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send_json(HTTPStatus.OK, self.server.application.health())
            return
        self._serve_static()

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            self._send_json(
                HTTPStatus.UNAUTHORIZED,
                {"error": "unauthorized", "message": "valid bearer token required"},
            )
            return
        path = self.path.split("?", 1)[0]
        routes = {
            "/api/seed": self.server.application.seed,
            "/api/compile": self.server.application.compile,
            "/api/ask": self.server.application.ask,
        }
        handler = routes.get(path)
        if handler is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            result = handler(self._read_json())
        except RequestError as exc:
            self._send_json(exc.status, {"error": "invalid_request", "message": str(exc)})
            return
        except (RuntimeUnavailableError, RuntimeCallError) as exc:
            self._send_json(
                HTTPStatus.BAD_GATEWAY,
                {"error": "model_runtime_error", "message": str(exc)},
            )
            return
        except (ContextBudgetError, ProtectedSelectionError) as exc:
            self._send_json(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": "context_budget_error", "message": str(exc)},
            )
            return
        except StoreConflict as exc:
            self._send_json(
                HTTPStatus.CONFLICT,
                {"error": "write_conflict", "message": str(exc)},
            )
            return
        except StoreCorruption:
            self.log_error("operation failed: StoreCorruption")
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "integrity_error", "message": "stored data failed integrity checks"},
            )
            return
        except (OSError, ValueError) as exc:
            self.log_error("operation failed: %s", type(exc).__name__)
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "internal_error", "message": "operation failed"},
            )
            return
        self._send_json(HTTPStatus.OK, result)

    def log_message(self, format: str, *args: object) -> None:
        # Retain the standard concise access log, but never log request bodies.
        super().log_message(format, *args)


def make_server(
    *,
    host: str = "127.0.0.1",
    port: int | None = None,
    db_path: str | Path | None = None,
    client: ResponsesClient | None = None,
    model: str | None = None,
    auth_token: str | None = None,
    enable_live_http: bool = False,
) -> AcheonHTTPServer:
    """Create, but do not start, an HTTP server (useful for tests)."""

    if port is None:
        try:
            port = int(os.environ.get("PORT", "8000"))
        except ValueError as exc:
            raise ValueError("PORT must be an integer") from exc
    if not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    resolved_token = (
        auth_token.strip()
        if auth_token is not None
        else os.environ.get("ACHEON_HTTP_TOKEN", "").strip()
    )
    token = resolved_token or None
    if host not in {"127.0.0.1", "localhost", "::1"} and (token is None or len(token) < 16):
        raise ValueError(
            "non-loopback HTTP binding requires ACHEON_HTTP_TOKEN with at least 16 characters"
        )
    if enable_live_http and (token is None or len(token) < 16):
        raise ValueError("live HTTP mode requires ACHEON_HTTP_TOKEN with at least 16 characters")
    resolved_db = db_path if db_path is not None else os.environ.get("ACHEON_DB", "data/acheon.db")
    application = AcheonApplication.create(
        db_path=resolved_db,
        client=client,
        model=model,
        auth_token=token,
        enable_live_http=enable_live_http,
    )
    try:
        return AcheonHTTPServer((host, port), application)
    except Exception:
        application.close()
        raise


def serve(
    *,
    host: str = "127.0.0.1",
    port: int | None = None,
    db_path: str | Path | None = None,
    client: ResponsesClient | None = None,
    model: str | None = None,
    enable_live_http: bool = False,
) -> None:
    server = make_server(
        host=host,
        port=port,
        db_path=db_path,
        client=client,
        model=model,
        enable_live_http=enable_live_http,
    )
    address, actual_port = server.server_address[:2]
    mode = server.application.health()["mode"]
    print(f"Acheon listening on http://{address}:{actual_port} ({mode}, {model or DEFAULT_MODEL})")
    try:
        server.serve_forever()
    finally:
        server.server_close()
        server.application.close()


__all__ = [
    "AcheonApplication",
    "AcheonHTTPServer",
    "AcheonRequestHandler",
    "make_server",
    "serve",
]
