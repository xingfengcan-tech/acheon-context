"""Command-line interface for Acheon's deterministic and optional online paths."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from typing import Any

from .compiler import ContextCompiler
from .demo import DEMO_NAMESPACE, DEMO_QUERY, run_demo, seed_demo
from .models import CompileConfig
from .runtime import (
    DEFAULT_MODEL,
    AcheonRuntime,
    OpenAIResponsesAdapter,
    RuntimeCallError,
    RuntimeUnavailableError,
)
from .store import MemoryStore


def _default_db() -> str:
    return os.environ.get("ACHEON_DB", "data/acheon.db")


def _default_port() -> int:
    raw = os.environ.get("PORT", "8000")
    try:
        port = int(raw)
    except ValueError as exc:
        raise ValueError("PORT must be an integer") from exc
    if not 0 <= port <= 65535:
        raise ValueError("PORT must be between 0 and 65535")
    return port


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _packet_summary(packet: Any) -> None:
    print(f"namespace: {packet.namespace}")
    print(f"budget: {packet.used_tokens}/{packet.budget_tokens} estimated tokens")
    print(f"selected: {', '.join(packet.selected_ids) if packet.selected_ids else '(none)'}")
    print(f"digest: {packet.digest}")
    print("\nCompiled context\n----------------")
    print(packet.context)
    print("\nSelection trace\n---------------")
    for decision in packet.decisions:
        marker = "+" if decision.selected else "-"
        reasons = ", ".join(decision.reason_codes)
        print(f"{marker} {decision.record_id}: {reasons}")


def _add_db_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--db",
        default=_default_db(),
        help="SQLite database path (default: ACHEON_DB or data/acheon.db)",
    )


def _add_compile_arguments(parser: argparse.ArgumentParser, *, default_query: str | None) -> None:
    if default_query is None:
        parser.add_argument("query", help="Task used to select relevant context")
    else:
        parser.add_argument("query", nargs="?", default=default_query)
    parser.add_argument("--namespace", default=DEMO_NAMESPACE)
    parser.add_argument(
        "--scope",
        action="append",
        dest="scopes",
        help="Requested scope; repeat for multiple scopes (global is always included)",
    )
    parser.add_argument("--budget", type=int, default=800, dest="budget_tokens")
    parser.add_argument("--json", action="store_true", dest="as_json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="acheon",
        description="Auditable, deterministic context orchestration for AI workflows.",
    )
    parser.add_argument("--version", action="version", version="acheon 0.1.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed", help="Add the public sample corpus")
    _add_db_argument(seed_parser)
    seed_parser.add_argument("--namespace", default=DEMO_NAMESPACE)
    seed_parser.add_argument("--json", action="store_true", dest="as_json")
    seed_parser.set_defaults(handler=_cmd_seed)

    compile_parser = subparsers.add_parser(
        "compile", help="Compile a bounded context packet without calling a model"
    )
    _add_db_argument(compile_parser)
    _add_compile_arguments(compile_parser, default_query=None)
    compile_parser.set_defaults(handler=_cmd_compile)

    demo_parser = subparsers.add_parser("demo", help="Run a credential-free in-memory demo")
    _add_compile_arguments(demo_parser, default_query=DEMO_QUERY)
    demo_parser.add_argument(
        "--db",
        default=":memory:",
        help="Optional database path; defaults to an isolated in-memory store",
    )
    demo_parser.set_defaults(handler=_cmd_demo)

    serve_parser = subparsers.add_parser("serve", help="Start the local HTTP demo")
    _add_db_argument(serve_parser)
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=None, help="Default: PORT or 8000")
    serve_parser.add_argument("--model", default=None, help=f"Default: {DEFAULT_MODEL}")
    serve_parser.add_argument(
        "--enable-live-http",
        action="store_true",
        help="Permit model calls over HTTP; requires ACHEON_HTTP_TOKEN",
    )
    serve_parser.set_defaults(handler=_cmd_serve)

    ask_parser = subparsers.add_parser(
        "ask", help="Compile context and call GPT-5.6, or preview without credentials"
    )
    _add_db_argument(ask_parser)
    _add_compile_arguments(ask_parser, default_query=None)
    ask_parser.add_argument("--model", default=None, help=f"Default: {DEFAULT_MODEL}")
    ask_parser.add_argument(
        "--reasoning-effort",
        choices=("none", "low", "medium", "high", "xhigh", "max"),
        default="low",
    )
    ask_parser.add_argument(
        "--preview",
        action="store_true",
        help="Prepare the request without making an API call, even if a key is configured",
    )
    ask_parser.set_defaults(handler=_cmd_ask)
    return parser


def _validated_budget(value: int) -> int:
    if value < 160:
        raise ValueError("budget must be at least 160 estimated tokens")
    return value


def _scopes(args: argparse.Namespace) -> tuple[str, ...]:
    return tuple(args.scopes or ("global",))


def _cmd_seed(args: argparse.Namespace) -> int:
    with MemoryStore(args.db) as store:
        result = seed_demo(store, args.namespace)
        result["audit_valid"] = store.verify_audit()
    if args.as_json:
        _print_json(result)
    else:
        print(
            f"Seeded namespace '{args.namespace}': {len(result['added'])} added, "
            f"{len(result['skipped'])} already present."
        )
        print(f"Audit chain valid: {result['audit_valid']}")
    return 0


def _cmd_compile(args: argparse.Namespace) -> int:
    config = CompileConfig(budget_tokens=_validated_budget(args.budget_tokens))
    with MemoryStore(args.db) as store:
        packet = ContextCompiler(store, config).compile(
            query=args.query,
            namespace=args.namespace,
            scopes=_scopes(args),
        )
    if args.as_json:
        _print_json(packet.to_dict())
    else:
        _packet_summary(packet)
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    report = run_demo(
        query=args.query,
        namespace=args.namespace,
        budget_tokens=_validated_budget(args.budget_tokens),
        db_path=args.db,
    )
    if args.as_json:
        _print_json(report)
    else:
        print("Acheon offline demo (no model call)\n")
        packet = report["packet"]
        print(f"audit chain valid: {report['audit_valid']}")
        print(f"selected: {', '.join(packet['selected_ids'])}")
        print(f"budget: {packet['used_tokens']}/{packet['budget_tokens']} estimated tokens")
        print(f"digest: {packet['digest']}")
        print("\n" + packet["context"])
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    from .server import serve

    port = _default_port() if args.port is None else args.port
    if not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    serve(
        host=args.host,
        port=port,
        db_path=args.db,
        model=args.model,
        enable_live_http=args.enable_live_http,
    )
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    config = CompileConfig(budget_tokens=_validated_budget(args.budget_tokens))
    adapter = OpenAIResponsesAdapter(
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        force_preview=args.preview,
    )
    with MemoryStore(args.db) as store:
        runtime = AcheonRuntime(
            store,
            compiler=ContextCompiler(store, config),
            adapter=adapter,
        )
        result = runtime.ask(args.query, namespace=args.namespace, scopes=_scopes(args))
    if args.as_json:
        _print_json(result.to_dict())
    else:
        _packet_summary(result.packet)
        print("\nModel result\n------------")
        if result.preview_only:
            print("preview_only: no API credential was used and no online answer was generated.")
            print("Use --json to inspect the prepared request.")
        else:
            print(f"status: {result.model_run.status}")
            print(result.answer or "(The provider returned no text output.)")
            if result.model_run.response_id:
                print(f"\nresponse id: {result.model_run.response_id}")
            if result.model_run.request_id:
                print(f"request id: {result.model_run.request_id}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return int(args.handler(args))
    except (ValueError, OSError, RuntimeUnavailableError, RuntimeCallError) as exc:
        print(f"acheon: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nacheon: stopped", file=sys.stderr)
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
