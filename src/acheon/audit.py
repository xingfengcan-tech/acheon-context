"""Canonical serialization and tamper-evident audit helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

ZERO_HASH = "0" * 64


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def digest_json(value: Any) -> str:
    return digest_text(canonical_json(value))


@dataclass(frozen=True, slots=True)
class AuditEvent:
    sequence: int
    occurred_at: str
    action: str
    namespace: str
    record_id: str | None
    previous_hash: str
    payload_json: str
    state_hash: str
    event_hash: str

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        occurred_at: str,
        action: str,
        namespace: str,
        record_id: str | None,
        previous_hash: str,
        payload: dict[str, Any],
        state_hash: str,
    ) -> AuditEvent:
        payload_json = canonical_json(payload)
        body = {
            "sequence": sequence,
            "occurred_at": occurred_at,
            "action": action,
            "namespace": namespace,
            "record_id": record_id,
            "previous_hash": previous_hash,
            "payload_json": payload_json,
            "state_hash": state_hash,
        }
        return cls(
            sequence=sequence,
            occurred_at=occurred_at,
            action=action,
            namespace=namespace,
            record_id=record_id,
            previous_hash=previous_hash,
            payload_json=payload_json,
            state_hash=state_hash,
            event_hash=digest_json(body),
        )

    def verify_hash(self) -> bool:
        try:
            payload = json.loads(self.payload_json)
        except (json.JSONDecodeError, TypeError, ValueError):
            return False
        if not isinstance(payload, dict):
            return False
        return (
            self.event_hash
            == AuditEvent.create(
                sequence=self.sequence,
                occurred_at=self.occurred_at,
                action=self.action,
                namespace=self.namespace,
                record_id=self.record_id,
                previous_hash=self.previous_hash,
                payload=payload,
                state_hash=self.state_hash,
            ).event_hash
        )


def verify_chain(events: list[AuditEvent]) -> bool:
    previous = ZERO_HASH
    for expected_sequence, event in enumerate(events, start=1):
        if event.sequence != expected_sequence:
            return False
        if event.previous_hash != previous or not event.verify_hash():
            return False
        previous = event.event_hash
    return True
