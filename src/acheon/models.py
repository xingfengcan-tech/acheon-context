"""Immutable domain objects for records, selection, and compiled context."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from .audit import canonical_json, digest_json
from .text import estimate_tokens

_PINNED_INSTRUCTION_MIN_CONFIDENCE = 0.8


def utc_now() -> datetime:
    return datetime.now(UTC)


def _ensure_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


class MemoryKind(StrEnum):
    INSTRUCTION = "instruction"
    DECISION = "decision"
    PREFERENCE = "preference"
    FACT = "fact"
    EVIDENCE = "evidence"
    EVENT = "event"
    ARTIFACT = "artifact"
    OPEN_LOOP = "open_loop"
    SUMMARY = "summary"


class RecordState(StrEnum):
    ACTIVE = "active"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"
    EXPIRED = "expired"


class TrustClass(StrEnum):
    USER_CONFIRMED = "user_confirmed"
    VERIFIED = "verified"
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNTRUSTED = "untrusted"


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    record_id: str
    namespace: str
    text: str
    kind: MemoryKind = MemoryKind.FACT
    revision: int = 1
    state: RecordState = RecordState.ACTIVE
    topic: str = ""
    scopes: tuple[str, ...] = ("global",)
    tags: tuple[str, ...] = ()
    source: str = "manual"
    trust: TrustClass = TrustClass.OBSERVED
    confidence: float = 0.8
    created_at: datetime = field(default_factory=utc_now)
    valid_until: datetime | None = None
    supersedes: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    conflicts_with: tuple[str, ...] = ()
    pinned: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.record_id or len(self.record_id) > 128:
            raise ValueError("record_id must be 1..128 characters")
        if not self.namespace or len(self.namespace) > 128:
            raise ValueError("namespace must be 1..128 characters")
        if not self.text.strip():
            raise ValueError("text cannot be empty")
        if self.revision < 1:
            raise ValueError("revision must be positive")
        if not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be finite and in [0, 1]")
        _ensure_aware(self.created_at, "created_at")
        if self.valid_until is not None:
            _ensure_aware(self.valid_until, "valid_until")
            if self.valid_until <= self.created_at:
                raise ValueError("valid_until must be after created_at")
        object.__setattr__(self, "kind", MemoryKind(self.kind))
        object.__setattr__(self, "state", RecordState(self.state))
        object.__setattr__(self, "trust", TrustClass(self.trust))
        if not isinstance(self.pinned, bool):
            raise ValueError("pinned must be a boolean")
        if (
            self.pinned
            and self.kind is MemoryKind.INSTRUCTION
            and (
                self.trust is not TrustClass.USER_CONFIRMED
                or self.confidence < _PINNED_INSTRUCTION_MIN_CONFIDENCE
            )
        ):
            raise ValueError(
                "pinned instructions require user_confirmed trust and confidence >= 0.8"
            )
        for name in ("scopes", "tags", "supersedes", "requires", "conflicts_with"):
            values = tuple(str(item) for item in getattr(self, name))
            if any(not item for item in values):
                raise ValueError(f"{name} cannot contain empty values")
            if name in {"supersedes", "requires", "conflicts_with"}:
                if len(values) != len(set(values)):
                    raise ValueError(f"{name} cannot contain duplicate record IDs")
                if self.record_id in values:
                    raise ValueError(f"{name} cannot reference the record itself")
            object.__setattr__(self, name, values)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def token_estimate(self) -> int:
        return estimate_tokens(canonical_json(self.context_entry()))

    def context_entry(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.record_id,
            "kind": self.kind.value,
            "state": self.state.value,
            "topic": self.topic,
            "trust": self.trust.value,
            "source": self.source,
            "content": self.text,
        }
        if self.requires:
            payload["requires"] = list(self.requires)
        if self.conflicts_with:
            payload["conflicts_with"] = list(self.conflicts_with)
        return payload

    @property
    def checksum(self) -> str:
        return digest_json(self.to_dict())

    def is_live(self, *, as_of: datetime) -> bool:
        if self.state not in {RecordState.ACTIVE, RecordState.DISPUTED}:
            return False
        if self.created_at > as_of:
            return False
        return self.valid_until is None or self.valid_until > as_of

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "namespace": self.namespace,
            "text": self.text,
            "kind": self.kind.value,
            "revision": self.revision,
            "state": self.state.value,
            "topic": self.topic,
            "scopes": list(self.scopes),
            "tags": list(self.tags),
            "source": self.source,
            "trust": self.trust.value,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "supersedes": list(self.supersedes),
            "requires": list(self.requires),
            "conflicts_with": list(self.conflicts_with),
            "pinned": self.pinned,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> MemoryRecord:
        payload = dict(value)
        payload["created_at"] = datetime.fromisoformat(str(payload["created_at"]))
        if payload.get("valid_until"):
            payload["valid_until"] = datetime.fromisoformat(str(payload["valid_until"]))
        for name in ("scopes", "tags", "supersedes", "requires", "conflicts_with"):
            payload[name] = tuple(payload.get(name, ()))
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    relevance: float
    rank_fusion: float
    scope: float
    continuity: float
    trust: float
    recency: float
    diversity: float
    total: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SelectionDecision:
    record_id: str
    selected: bool
    reason_codes: tuple[str, ...]
    token_cost: int
    score: ScoreBreakdown | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "selected": self.selected,
            "reason_codes": list(self.reason_codes),
            "token_cost": self.token_cost,
            "score": self.score.to_dict() if self.score else None,
        }


@dataclass(frozen=True, slots=True)
class SelectionPlan:
    selected: tuple[MemoryRecord, ...]
    decisions: tuple[SelectionDecision, ...]
    budget_tokens: int
    selected_tokens: int
    policy_version: str


@dataclass(frozen=True, slots=True)
class ContextPacket:
    query: str
    namespace: str
    budget_tokens: int
    used_tokens: int
    selected_ids: tuple[str, ...]
    context: str
    digest: str
    audit_head: str
    decisions: tuple[SelectionDecision, ...]
    policy_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "namespace": self.namespace,
            "budget_tokens": self.budget_tokens,
            "used_tokens": self.used_tokens,
            "selected_ids": list(self.selected_ids),
            "context": self.context,
            "digest": self.digest,
            "audit_head": self.audit_head,
            "decisions": [decision.to_dict() for decision in self.decisions],
            "policy_version": self.policy_version,
        }


@dataclass(frozen=True, slots=True)
class CompileConfig:
    budget_tokens: int = 1200
    candidate_limit: int = 96
    protected_fraction: float = 0.28
    continuity_fraction: float = 0.24
    evidence_fraction: float = 0.20
    mmr_lambda: float = 0.76
    recency_half_life_days: float = 45.0
    use_scope_filter: bool = True
    use_lifecycle_filter: bool = True
    use_rank_fusion: bool = True
    use_diversity: bool = True
    use_dependencies: bool = True
    use_lane_reservation: bool = True
    policy_version: str = "acheon-selector-v1"

    def __post_init__(self) -> None:
        if self.budget_tokens < 160:
            raise ValueError("budget_tokens must be at least 160")
        if self.candidate_limit < 1:
            raise ValueError("candidate_limit must be positive")
        if not 0 <= self.mmr_lambda <= 1:
            raise ValueError("mmr_lambda must be in [0, 1]")
        fractions = (self.protected_fraction, self.continuity_fraction, self.evidence_fraction)
        if any(not 0 <= fraction <= 1 for fraction in fractions):
            raise ValueError("lane fractions must be in [0, 1]")
        if sum(fractions) > 0.9:
            raise ValueError("lane fractions leave too little shared capacity")
