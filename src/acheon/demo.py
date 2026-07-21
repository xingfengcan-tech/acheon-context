"""Deterministic sample data and a credential-free Acheon demonstration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .compiler import ContextCompiler
from .models import CompileConfig, MemoryKind, MemoryRecord, RecordState, TrustClass
from .store import MemoryStore

DEMO_NAMESPACE = "demo"
DEMO_QUERY = "What should we verify before shipping the offline developer demo?"
_DEMO_TIME = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)


def demo_records(namespace: str = DEMO_NAMESPACE) -> tuple[MemoryRecord, ...]:
    """Return a fixed, public sample corpus suitable for tests and screenshots."""

    return (
        MemoryRecord(
            record_id=f"{namespace}-product-boundary",
            namespace=namespace,
            text=(
                "Describe Acheon as an optional application-layer context orchestrator; "
                "do not claim changes to model weights or provider limits."
            ),
            kind=MemoryKind.INSTRUCTION,
            topic="product boundary",
            tags=("release", "claims"),
            trust=TrustClass.USER_CONFIRMED,
            confidence=1.0,
            pinned=True,
            created_at=_DEMO_TIME,
        ),
        MemoryRecord(
            record_id=f"{namespace}-offline-first",
            namespace=namespace,
            text="The core demo and benchmark must run without network access or API credentials.",
            kind=MemoryKind.DECISION,
            topic="offline demo",
            tags=("demo", "verification"),
            trust=TrustClass.VERIFIED,
            confidence=1.0,
            created_at=_DEMO_TIME + timedelta(minutes=1),
        ),
        MemoryRecord(
            record_id=f"{namespace}-retired-port-plan",
            namespace=namespace,
            text="The retired deployment plan used a fixed port and had no readiness endpoint.",
            kind=MemoryKind.DECISION,
            state=RecordState.SUPERSEDED,
            topic="deployment readiness",
            tags=("server", "release"),
            trust=TrustClass.OBSERVED,
            confidence=0.9,
            created_at=_DEMO_TIME + timedelta(minutes=1, seconds=30),
        ),
        MemoryRecord(
            record_id=f"{namespace}-readiness",
            namespace=namespace,
            text="The HTTP service exposes /health and reads its listening port from PORT.",
            kind=MemoryKind.FACT,
            topic="deployment readiness",
            tags=("server", "health", "port"),
            trust=TrustClass.VERIFIED,
            confidence=0.98,
            created_at=_DEMO_TIME + timedelta(minutes=2),
        ),
        MemoryRecord(
            record_id=f"{namespace}-test-contract",
            namespace=namespace,
            text=(
                "Release verification includes unit tests, a deterministic benchmark artifact, "
                "and the release verification script."
            ),
            kind=MemoryKind.EVIDENCE,
            topic="release checks",
            tags=("tests", "benchmark", "release"),
            trust=TrustClass.VERIFIED,
            confidence=0.96,
            requires=(f"{namespace}-offline-first",),
            created_at=_DEMO_TIME + timedelta(minutes=3),
        ),
        MemoryRecord(
            record_id=f"{namespace}-traceability",
            namespace=namespace,
            text="Show selected record IDs, reason codes, budget usage, and the packet receipt.",
            kind=MemoryKind.PREFERENCE,
            topic="trace output",
            tags=("audit", "explainability"),
            trust=TrustClass.USER_CONFIRMED,
            confidence=0.95,
            created_at=_DEMO_TIME + timedelta(minutes=4),
        ),
        MemoryRecord(
            record_id=f"{namespace}-online-eval",
            namespace=namespace,
            text=(
                "Live GPT-5.6 evidence must be reported separately before claiming "
                "downstream answer improvement over deterministic offline evidence."
            ),
            kind=MemoryKind.OPEN_LOOP,
            topic="online evaluation",
            tags=("gpt-5.6", "evidence"),
            trust=TrustClass.OBSERVED,
            confidence=0.9,
            created_at=_DEMO_TIME + timedelta(minutes=5),
        ),
        MemoryRecord(
            record_id=f"{namespace}-unrelated-theme",
            namespace=namespace,
            text="A future visual theme could offer a compact high-contrast mode.",
            kind=MemoryKind.EVENT,
            topic="future interface",
            tags=("ui",),
            trust=TrustClass.INFERRED,
            confidence=0.5,
            scopes=("design",),
            created_at=_DEMO_TIME + timedelta(minutes=6),
        ),
    )


def seed_demo(store: MemoryStore, namespace: str = DEMO_NAMESPACE) -> dict[str, Any]:
    """Add missing sample records without revising or deleting existing records."""

    existing = {record.record_id for record in store.current_records(namespace)}
    added: list[str] = []
    skipped: list[str] = []
    for record in demo_records(namespace):
        if record.record_id in existing:
            skipped.append(record.record_id)
            continue
        store.add(record)
        existing.add(record.record_id)
        added.append(record.record_id)
    return {"namespace": namespace, "added": added, "skipped": skipped}


def run_demo(
    *,
    query: str = DEMO_QUERY,
    namespace: str = DEMO_NAMESPACE,
    budget_tokens: int = 800,
    db_path: str | Path = ":memory:",
) -> dict[str, Any]:
    """Run the complete deterministic path and return a JSON-ready report."""

    with MemoryStore(db_path) as store:
        seeded = seed_demo(store, namespace)
        compiler = ContextCompiler(store, CompileConfig(budget_tokens=budget_tokens))
        packet = compiler.compile(query=query, namespace=namespace)
        return {
            "mode": "offline",
            "online_model_called": False,
            "seed": seeded,
            "packet": packet.to_dict(),
            "audit_valid": store.verify_audit(),
        }


__all__ = [
    "DEMO_NAMESPACE",
    "DEMO_QUERY",
    "demo_records",
    "run_demo",
    "seed_demo",
]
