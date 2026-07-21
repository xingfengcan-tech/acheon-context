"""Deterministic, budget-matched retrieval baselines.

The baselines intentionally model simple history truncation and bag-of-words
retrieval.  They do not inspect lifecycle, scope, dependency, or trust fields.
That makes them useful controls for the orchestration policy rather than weaker
reimplementations of it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .models import MemoryRecord
from .rendering import rendered_token_cost
from .text import overlap_score, tokenize

RENDER_POLICY_VERSION = "acheon-selector-v1"
PACKET_OVERHEAD_TOKENS = rendered_token_cost((), policy_version=RENDER_POLICY_VERSION)


@dataclass(frozen=True, slots=True)
class BaselineSelection:
    """A minimal selection result shared by all offline baselines."""

    name: str
    selected: tuple[MemoryRecord, ...]
    budget_tokens: int
    selected_tokens: int

    @property
    def selected_ids(self) -> tuple[str, ...]:
        return tuple(record.record_id for record in self.selected)


def usable_content_budget(budget_tokens: int) -> int:
    """Return the record budget after the common packet framing reserve."""

    if budget_tokens < 0:
        raise ValueError("budget_tokens cannot be negative")
    return max(0, budget_tokens - PACKET_OVERHEAD_TOKENS)


def _take_prefix(
    records: Iterable[MemoryRecord],
    *,
    name: str,
    budget_tokens: int,
) -> BaselineSelection:
    selected: list[MemoryRecord] = []
    spent = PACKET_OVERHEAD_TOKENS
    for record in records:
        # These are truncation/top-k controls: once the next ranked entry no
        # longer fits, the visible prefix ends.
        proposed = [*selected, record]
        proposed_tokens = rendered_token_cost(
            proposed,
            policy_version=RENDER_POLICY_VERSION,
        )
        if proposed_tokens > budget_tokens:
            break
        selected.append(record)
        spent = proposed_tokens
    return BaselineSelection(
        name=name,
        selected=tuple(selected),
        budget_tokens=budget_tokens,
        selected_tokens=spent,
    )


def recent_tail(
    records: Iterable[MemoryRecord],
    *,
    query: str,
    budget_tokens: int,
) -> BaselineSelection:
    """Take the newest records that fit, ignoring record semantics."""

    del query
    ranked = sorted(records, key=lambda record: (-record.created_at.timestamp(), record.record_id))
    return _take_prefix(ranked, name="recent_tail", budget_tokens=budget_tokens)


def chronological_prefix(
    records: Iterable[MemoryRecord],
    *,
    query: str,
    budget_tokens: int,
) -> BaselineSelection:
    """Take the oldest chronological prefix that fits."""

    del query
    ranked = sorted(records, key=lambda record: (record.created_at.timestamp(), record.record_id))
    return _take_prefix(ranked, name="chronological_prefix", budget_tokens=budget_tokens)


def lexical_topk(
    records: Iterable[MemoryRecord],
    *,
    query: str,
    budget_tokens: int,
) -> BaselineSelection:
    """Rank records by deterministic lexical overlap, then take a prefix."""

    query_tokens = tokenize(query)

    def key(record: MemoryRecord) -> tuple[float, float, str]:
        document = tokenize(" ".join((record.text, record.topic, *record.tags, record.source)))
        return (
            -overlap_score(query_tokens, document),
            -record.created_at.timestamp(),
            record.record_id,
        )

    ranked = sorted(records, key=key)
    return _take_prefix(ranked, name="lexical_topk", budget_tokens=budget_tokens)


BASELINES: dict[
    str,
    Callable[..., BaselineSelection],
] = {
    "recent_tail": recent_tail,
    "chronological_prefix": chronological_prefix,
    "lexical_topk": lexical_topk,
}
