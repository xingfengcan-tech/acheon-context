"""Render selection plans as bounded, injection-aware context packets."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime

from .audit import digest_json
from .models import (
    CompileConfig,
    ContextPacket,
    MemoryRecord,
)
from .rendering import render_context
from .selector import ContextSelector
from .store import MemoryStore
from .text import estimate_tokens


class ContextBudgetError(ValueError):
    """Raised when the protected context bundle cannot fit the requested budget."""


class ContextCompiler:
    def __init__(self, store: MemoryStore, config: CompileConfig | None = None) -> None:
        self.store = store
        self.config = config or CompileConfig()
        self.selector = ContextSelector(self.config)

    @staticmethod
    def _render(records: Iterable[MemoryRecord], *, policy_version: str) -> str:
        return render_context(records, policy_version=policy_version)

    def compile(
        self,
        *,
        query: str,
        namespace: str,
        scopes: tuple[str, ...] = ("global",),
        as_of: datetime | None = None,
    ) -> ContextPacket:
        """Compile current revisions into a bounded context packet.

        ``as_of`` evaluates lifecycle timestamps on the store's current revision
        set. It does not reconstruct which revisions were current at a historical
        database point in time.
        """

        with self.store.compilation_snapshot(namespace) as snapshot:
            plan = self.selector.select(
                snapshot.records,
                query=query,
                scopes=scopes,
                as_of=as_of,
            )
            selected = list(plan.selected)
            decisions = list(plan.decisions)
            context = self._render(selected, policy_version=plan.policy_version)
            used_tokens = estimate_tokens(context)

            # The selector reserves framing overhead, but render-time enforcement is final.
            while used_tokens > self.config.budget_tokens and selected:
                required_ids = {
                    dependency_id for record in selected for dependency_id in record.requires
                }
                removable_index = next(
                    (
                        index
                        for index in range(len(selected) - 1, -1, -1)
                        if not selected[index].pinned
                        and selected[index].record_id not in required_ids
                    ),
                    -1,
                )
                if removable_index < 0:
                    raise ContextBudgetError(
                        "protected records and dependencies exceed the rendered estimate budget"
                    )
                removed = selected.pop(removable_index)
                decisions = [
                    replace(
                        decision,
                        selected=False,
                        reason_codes=tuple(
                            code
                            for code in decision.reason_codes
                            if not code.startswith("selected:")
                        )
                        + ("omitted:render_budget",),
                    )
                    if decision.record_id == removed.record_id
                    else decision
                    for decision in decisions
                ]
                context = self._render(selected, policy_version=plan.policy_version)
                used_tokens = estimate_tokens(context)

            if used_tokens > self.config.budget_tokens:
                raise ContextBudgetError("context envelope exceeds the rendered estimate budget")

            packet_body = {
                "query_digest": digest_json(query),
                "namespace": namespace,
                "budget_tokens": self.config.budget_tokens,
                "used_tokens": used_tokens,
                "selected_ids": [record.record_id for record in selected],
                "context": context,
                "policy_version": plan.policy_version,
            }
            packet_digest = digest_json(packet_body)
            event = snapshot.record_activity(
                payload={
                    "packet_digest": packet_digest,
                    "selected_ids": packet_body["selected_ids"],
                    "budget_tokens": self.config.budget_tokens,
                    "used_tokens": used_tokens,
                    "policy_version": plan.policy_version,
                    "source_state_hash": snapshot.state_hash,
                },
            )
            return ContextPacket(
                query=query,
                namespace=namespace,
                budget_tokens=self.config.budget_tokens,
                used_tokens=used_tokens,
                selected_ids=tuple(record.record_id for record in selected),
                context=context,
                digest=packet_digest,
                audit_head=event.event_hash,
                decisions=tuple(decisions),
                policy_version=plan.policy_version,
            )
