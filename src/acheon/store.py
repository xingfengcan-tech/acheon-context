"""SQLite-backed, append-oriented record store with a hash-chained audit log."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .audit import ZERO_HASH, AuditEvent, canonical_json, digest_json, digest_text, verify_chain
from .models import MemoryRecord, RecordState


class StoreConflict(RuntimeError):
    """Raised when a write does not match the current record revision."""


class RecordNotFound(KeyError):
    pass


class StoreCorruption(RuntimeError):
    """Raised when persisted record bytes do not match their stored checksum."""


@dataclass(slots=True)
class _CompilationSnapshot:
    """Verified records and receipt writer held inside one store transaction."""

    store: MemoryStore
    namespace: str
    records: tuple[MemoryRecord, ...]
    state_hash: str
    event: AuditEvent | None = None

    def record_activity(self, *, payload: dict[str, Any]) -> AuditEvent:
        if self.event is not None:
            raise RuntimeError("a compilation snapshot can record only one receipt")
        self.event = self.store._append_audit(
            action="context.compile",
            namespace=self.namespace,
            record_id=None,
            payload=payload,
        )
        return self.event


class MemoryStore:
    """Versioned local storage.

    Each update creates a new revision. Old revisions remain available for audit,
    while normal reads expose only the current revision. Audit payloads contain
    checksums and lifecycle metadata, never raw record text.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            self._connection.execute("PRAGMA journal_mode = WAL")
        self._create_schema()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_revisions (
                    record_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    namespace TEXT NOT NULL,
                    is_current INTEGER NOT NULL CHECK (is_current IN (0, 1)),
                    payload_json TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    PRIMARY KEY (record_id, revision)
                );

                CREATE UNIQUE INDEX IF NOT EXISTS one_current_revision
                ON memory_revisions(record_id)
                WHERE is_current = 1;

                CREATE INDEX IF NOT EXISTS current_namespace_records
                ON memory_revisions(namespace, is_current);

                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence INTEGER PRIMARY KEY,
                    occurred_at TEXT NOT NULL,
                    action TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    record_id TEXT,
                    previous_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    state_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE
                );
                """
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> MemoryStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _begin_verified_write(self) -> None:
        self._connection.execute("BEGIN IMMEDIATE")
        if not self.verify_audit():
            raise StoreCorruption("store integrity check failed before write")

    def _current_row(self, record_id: str) -> sqlite3.Row | None:
        return self._connection.execute(
            """
            SELECT record_id, revision, namespace, payload_json, checksum
            FROM memory_revisions
            WHERE record_id = ? AND is_current = 1
            """,
            (record_id,),
        ).fetchone()

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> MemoryRecord:
        try:
            record = MemoryRecord.from_dict(json.loads(row["payload_json"]))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise StoreCorruption("stored record payload is invalid") from exc
        redundant_fields = {
            "record_id": record.record_id,
            "revision": record.revision,
            "namespace": record.namespace,
        }
        if any(str(row[name]) != str(value) for name, value in redundant_fields.items()):
            raise StoreCorruption("stored record routing metadata mismatch")
        if record.checksum != str(row["checksum"]):
            raise StoreCorruption("stored record checksum mismatch")
        return record

    def _insert_revision(self, record: MemoryRecord) -> None:
        self._connection.execute(
            """
            INSERT INTO memory_revisions
                (record_id, revision, namespace, is_current, payload_json, checksum)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (
                record.record_id,
                record.revision,
                record.namespace,
                canonical_json(record.to_dict()),
                record.checksum,
            ),
        )

    def _replace_current(self, current: MemoryRecord, replacement: MemoryRecord) -> None:
        if replacement.record_id != current.record_id:
            raise StoreConflict("a revision cannot change record_id")
        if replacement.namespace != current.namespace:
            raise StoreConflict("a revision cannot move namespaces")
        if replacement.revision != current.revision + 1:
            raise StoreConflict("replacement revision must increment by one")
        updated = self._connection.execute(
            """
            UPDATE memory_revisions SET is_current = 0
            WHERE record_id = ? AND revision = ? AND is_current = 1
            """,
            (current.record_id, current.revision),
        )
        if updated.rowcount != 1:
            raise StoreConflict("current revision changed during transaction")
        self._insert_revision(replacement)

    def add(self, record: MemoryRecord) -> MemoryRecord:
        """Insert a new record and atomically mark explicit predecessors superseded."""

        with self._lock:
            try:
                self._begin_verified_write()
                if record.supersedes and not record.is_live(as_of=datetime.now(UTC)):
                    raise StoreConflict("a superseding record must be currently active or disputed")
                if self._current_row(record.record_id) is not None:
                    raise StoreConflict(f"record already exists: {record.record_id}")
                if record.revision != 1:
                    raise StoreConflict("new records must start at revision one")
                self._insert_revision(record)
                superseded: list[str] = []
                for target_id in record.supersedes:
                    row = self._current_row(target_id)
                    if row is None:
                        raise RecordNotFound(target_id)
                    current = self._record_from_row(row)
                    if current.namespace != record.namespace:
                        raise StoreConflict("cannot supersede a record in another namespace")
                    if current.state not in {RecordState.ACTIVE, RecordState.DISPUTED}:
                        raise StoreConflict("can only supersede an active or disputed record")
                    replacement = replace(
                        current,
                        revision=current.revision + 1,
                        state=RecordState.SUPERSEDED,
                    )
                    self._replace_current(current, replacement)
                    superseded.append(target_id)
                self._append_audit(
                    action="record.add",
                    namespace=record.namespace,
                    record_id=record.record_id,
                    payload={
                        "checksum": record.checksum,
                        "kind": record.kind.value,
                        "revision": record.revision,
                        "superseded": superseded,
                    },
                )
                self._connection.commit()
                return record
            except Exception:
                self._connection.rollback()
                raise

    def revise(
        self,
        record_id: str,
        *,
        expected_revision: int | None = None,
        action: str = "record.revise",
        **changes: Any,
    ) -> MemoryRecord:
        """Create a checked new revision of an existing record."""

        forbidden = {
            "record_id",
            "revision",
            "namespace",
            "created_at",
            "supersedes",
        } & changes.keys()
        if forbidden:
            raise StoreConflict(f"immutable fields cannot be revised: {sorted(forbidden)}")
        with self._lock:
            try:
                self._begin_verified_write()
                row = self._current_row(record_id)
                if row is None:
                    raise RecordNotFound(record_id)
                current = self._record_from_row(row)
                if expected_revision is not None and current.revision != expected_revision:
                    raise StoreConflict(
                        f"expected revision {expected_revision}, found {current.revision}"
                    )
                requested_state = RecordState(changes.get("state", current.state))
                if current.state is RecordState.SUPERSEDED and requested_state in {
                    RecordState.ACTIVE,
                    RecordState.DISPUTED,
                }:
                    raise StoreConflict(
                        "a superseded record cannot be reactivated without an atomic rollback"
                    )
                replacement = replace(current, revision=current.revision + 1, **changes)
                self._replace_current(current, replacement)
                self._append_audit(
                    action=action,
                    namespace=current.namespace,
                    record_id=record_id,
                    payload={
                        "before_checksum": current.checksum,
                        "after_checksum": replacement.checksum,
                        "before_revision": current.revision,
                        "after_revision": replacement.revision,
                        "changed_fields": sorted(changes),
                    },
                )
                self._connection.commit()
                return replacement
            except Exception:
                self._connection.rollback()
                raise

    def transition(
        self,
        record_id: str,
        state: RecordState,
        *,
        expected_revision: int | None = None,
    ) -> MemoryRecord:
        state = RecordState(state)
        return self.revise(
            record_id,
            expected_revision=expected_revision,
            action=f"record.{state.value}",
            state=state,
        )

    def forget(self, record_id: str, *, expected_revision: int | None = None) -> MemoryRecord:
        return self.transition(
            record_id,
            RecordState.REVOKED,
            expected_revision=expected_revision,
        )

    def get(self, record_id: str, *, revision: int | None = None) -> MemoryRecord:
        with self._lock:
            if revision is None:
                row = self._current_row(record_id)
            else:
                row = self._connection.execute(
                    """
                    SELECT record_id, revision, namespace, payload_json, checksum
                    FROM memory_revisions WHERE record_id = ? AND revision = ?
                    """,
                    (record_id, revision),
                ).fetchone()
            if row is None:
                raise RecordNotFound(record_id)
            return self._record_from_row(row)

    def history(self, record_id: str) -> tuple[MemoryRecord, ...]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT record_id, revision, namespace, payload_json, checksum
                FROM memory_revisions WHERE record_id = ? ORDER BY revision
                """,
                (record_id,),
            ).fetchall()
            if not rows:
                raise RecordNotFound(record_id)
            return tuple(self._record_from_row(row) for row in rows)

    def current_records(self, namespace: str) -> tuple[MemoryRecord, ...]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT record_id, revision, namespace, payload_json, checksum
                FROM memory_revisions
                WHERE namespace = ? AND is_current = 1
                ORDER BY record_id
                """,
                (namespace,),
            ).fetchall()
            return tuple(self._record_from_row(row) for row in rows)

    @contextmanager
    def compilation_snapshot(self, namespace: str) -> Iterator[_CompilationSnapshot]:
        """Hold selection records and their audit receipt in one verified snapshot."""

        with self._lock:
            try:
                self._begin_verified_write()
                records = self.current_records(namespace)
                snapshot = _CompilationSnapshot(
                    store=self,
                    namespace=namespace,
                    records=records,
                    state_hash=self._state_hash(),
                )
                yield snapshot
                if snapshot.event is None:
                    raise RuntimeError("compilation snapshot closed without an audit receipt")
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    def namespaces(self) -> tuple[str, ...]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT DISTINCT namespace FROM memory_revisions
                WHERE is_current = 1 ORDER BY namespace
                """
            ).fetchall()
            return tuple(str(row["namespace"]) for row in rows)

    def _state_hash(self) -> str:
        rows = self._connection.execute(
            """
            SELECT record_id, revision, namespace, is_current, payload_json, checksum
            FROM memory_revisions
            ORDER BY record_id, revision
            """
        ).fetchall()
        return digest_json(
            [
                {
                    "record_id": row["record_id"],
                    "revision": row["revision"],
                    "namespace": row["namespace"],
                    "is_current": row["is_current"],
                    "payload_digest": digest_text(str(row["payload_json"])),
                    "stored_checksum": row["checksum"],
                }
                for row in rows
            ]
        )

    def _append_audit(
        self,
        *,
        action: str,
        namespace: str,
        record_id: str | None,
        payload: dict[str, Any],
    ) -> AuditEvent:
        last = self._connection.execute(
            "SELECT sequence, event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        sequence = 1 if last is None else int(last["sequence"]) + 1
        previous_hash = ZERO_HASH if last is None else str(last["event_hash"])
        event = AuditEvent.create(
            sequence=sequence,
            occurred_at=datetime.now(UTC).isoformat(),
            action=action,
            namespace=namespace,
            record_id=record_id,
            previous_hash=previous_hash,
            payload=payload,
            state_hash=self._state_hash(),
        )
        self._connection.execute(
            """
            INSERT INTO audit_events
                (sequence, occurred_at, action, namespace, record_id, previous_hash,
                 payload_json, state_hash, event_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.sequence,
                event.occurred_at,
                event.action,
                event.namespace,
                event.record_id,
                event.previous_hash,
                event.payload_json,
                event.state_hash,
                event.event_hash,
            ),
        )
        return event

    def record_activity(
        self,
        *,
        action: str,
        namespace: str,
        payload: dict[str, Any],
    ) -> AuditEvent:
        with self._lock:
            try:
                self._begin_verified_write()
                event = self._append_audit(
                    action=action,
                    namespace=namespace,
                    record_id=None,
                    payload=payload,
                )
                self._connection.commit()
                return event
            except Exception:
                self._connection.rollback()
                raise

    def audit_events(self) -> list[AuditEvent]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM audit_events ORDER BY sequence"
            ).fetchall()
            return [
                AuditEvent(
                    sequence=int(row["sequence"]),
                    occurred_at=str(row["occurred_at"]),
                    action=str(row["action"]),
                    namespace=str(row["namespace"]),
                    record_id=row["record_id"],
                    previous_hash=str(row["previous_hash"]),
                    payload_json=str(row["payload_json"]),
                    state_hash=str(row["state_hash"]),
                    event_hash=str(row["event_hash"]),
                )
                for row in rows
            ]

    @property
    def audit_head(self) -> str:
        with self._lock:
            row = self._connection.execute(
                "SELECT event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            return ZERO_HASH if row is None else str(row["event_hash"])

    @property
    def state_hash(self) -> str:
        with self._lock:
            return self._state_hash()

    def verify_audit(self) -> bool:
        with self._lock:
            events = self.audit_events()
            if not verify_chain(events):
                return False
            if not events:
                row = self._connection.execute(
                    "SELECT COUNT(*) AS count FROM memory_revisions"
                ).fetchone()
                return row is not None and int(row["count"]) == 0
            return events[-1].state_hash == self._state_hash()
