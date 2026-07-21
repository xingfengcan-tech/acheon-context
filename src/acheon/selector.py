"""Deterministic multi-signal selection under an estimated-token budget."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import UTC, datetime

from .models import (
    CompileConfig,
    MemoryKind,
    MemoryRecord,
    RecordState,
    ScoreBreakdown,
    SelectionDecision,
    SelectionPlan,
    TrustClass,
)
from .rendering import rendered_token_cost
from .text import jaccard, normalize_text, overlap_score, tokenize

_KIND_PRIORITY = {
    MemoryKind.INSTRUCTION: 1.0,
    MemoryKind.DECISION: 0.88,
    MemoryKind.OPEN_LOOP: 0.82,
    MemoryKind.PREFERENCE: 0.72,
    MemoryKind.EVIDENCE: 0.64,
    MemoryKind.ARTIFACT: 0.60,
    MemoryKind.FACT: 0.58,
    MemoryKind.EVENT: 0.40,
    MemoryKind.SUMMARY: 0.34,
}

_TRUST_SCORE = {
    TrustClass.USER_CONFIRMED: 1.0,
    TrustClass.VERIFIED: 0.94,
    TrustClass.OBSERVED: 0.72,
    TrustClass.INFERRED: 0.42,
    TrustClass.UNTRUSTED: 0.12,
}

_LANES = {
    "protected": {MemoryKind.INSTRUCTION},
    "continuity": {MemoryKind.DECISION, MemoryKind.PREFERENCE, MemoryKind.OPEN_LOOP},
    "evidence": {MemoryKind.EVIDENCE, MemoryKind.ARTIFACT, MemoryKind.FACT},
    "general": {MemoryKind.EVENT, MemoryKind.SUMMARY},
}


class ProtectedSelectionError(ValueError):
    """Raised when an eligible protected record cannot be selected safely."""


def _rank_map(
    records: Iterable[MemoryRecord],
    key: Callable[[MemoryRecord], object],
) -> dict[str, int]:
    ordered = sorted(records, key=key)
    return {record.record_id: index for index, record in enumerate(ordered, start=1)}


class ContextSelector:
    """Select records using standard rank fusion, lane coverage, and MMR."""

    def __init__(self, config: CompileConfig | None = None) -> None:
        self.config = config or CompileConfig()

    def select(
        self,
        records: Iterable[MemoryRecord],
        *,
        query: str,
        scopes: tuple[str, ...] = ("global",),
        as_of: datetime | None = None,
    ) -> SelectionPlan:
        config = self.config
        moment = as_of or datetime.now(UTC)
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        requested_scopes = set(scopes) | {"global"}
        all_records = tuple(records)
        record_ids = [record.record_id for record in all_records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("record IDs must be unique within a selection")
        eligible: list[MemoryRecord] = []
        decision_reasons: dict[str, list[str]] = defaultdict(list)

        for record in all_records:
            if config.use_lifecycle_filter and not record.is_live(as_of=moment):
                if record.created_at > moment:
                    decision_reasons[record.record_id].append("omitted:not_yet_created")
                elif record.valid_until is not None and record.valid_until <= moment:
                    decision_reasons[record.record_id].append("omitted:expired")
                else:
                    decision_reasons[record.record_id].append(f"omitted:state:{record.state.value}")
                continue
            if config.use_scope_filter and not (set(record.scopes) & requested_scopes):
                decision_reasons[record.record_id].append("omitted:scope")
                continue
            eligible.append(record)

        query_tokens = tokenize(query)
        normalized_query = normalize_text(query)
        document_tokens = {
            record.record_id: tokenize(
                " ".join((record.text, record.topic, *record.tags, record.source))
            )
            for record in eligible
        }
        relevance = {
            record.record_id: overlap_score(query_tokens, document_tokens[record.record_id])
            for record in eligible
        }
        exact_reference = {
            record.record_id: float(
                any(
                    marker and normalize_text(marker) in normalized_query
                    for marker in (record.topic, record.source, *record.tags)
                )
            )
            for record in eligible
        }
        lexical_rank = _rank_map(
            eligible,
            lambda record: (-relevance[record.record_id], record.record_id),
        )
        exact_rank = _rank_map(
            eligible,
            lambda record: (-exact_reference[record.record_id], record.record_id),
        )
        kind_rank = _rank_map(
            eligible,
            lambda record: (-_KIND_PRIORITY[record.kind], record.record_id),
        )
        recency_rank = _rank_map(
            eligible,
            lambda record: (-record.created_at.timestamp(), record.record_id),
        )
        rank_sources = (lexical_rank, exact_rank, kind_rank, recency_rank)
        maximum_rrf = len(rank_sources) / 61.0

        scores: dict[str, ScoreBreakdown] = {}
        for record in eligible:
            age_days = max(0.0, (moment - record.created_at).total_seconds() / 86_400)
            recency = math.exp(-math.log(2) * age_days / max(config.recency_half_life_days, 0.001))
            rank_fusion = (
                sum(1.0 / (60 + ranks[record.record_id]) for ranks in rank_sources) / maximum_rrf
                if config.use_rank_fusion
                else relevance[record.record_id]
            )
            scope_score = 1.0 if set(record.scopes) & requested_scopes else 0.0
            continuity = max(_KIND_PRIORITY[record.kind], 1.0 if record.pinned else 0.0)
            trust = _TRUST_SCORE[record.trust] * record.confidence
            total = (
                0.36 * relevance[record.record_id]
                + 0.18 * rank_fusion
                + 0.10 * exact_reference[record.record_id]
                + 0.10 * scope_score
                + 0.14 * continuity
                + 0.07 * trust
                + 0.05 * recency
            )
            scores[record.record_id] = ScoreBreakdown(
                relevance=relevance[record.record_id],
                rank_fusion=rank_fusion,
                scope=scope_score,
                continuity=continuity,
                trust=trust,
                recency=recency,
                diversity=1.0,
                total=total,
            )

        eligible_by_id = {record.record_id: record for record in eligible}
        ranked = sorted(
            eligible,
            key=lambda record: (-scores[record.record_id].total, record.record_id),
        )
        pinned_candidates = [record for record in ranked if record.pinned]
        remaining_capacity = max(0, config.candidate_limit - len(pinned_candidates))
        candidates = (
            pinned_candidates
            + [record for record in ranked if not record.pinned][:remaining_capacity]
        )
        candidate_ids = {record.record_id for record in candidates}
        for record in ranked:
            if record.record_id in candidate_ids:
                continue
            decision_reasons[record.record_id].append("omitted:candidate_limit")

        base_tokens = rendered_token_cost((), policy_version=config.policy_version)
        usable_budget = max(0, config.budget_tokens - base_tokens)
        selected: list[MemoryRecord] = []
        selected_ids: set[str] = set()
        spent = base_tokens

        def mark_selected(record_id: str, reason: str) -> None:
            final_reasons = [
                code for code in decision_reasons[record_id] if not code.startswith("omitted:")
            ]
            if reason not in final_reasons:
                final_reasons.append(reason)
            decision_reasons[record_id] = final_reasons

        def selection_bundle(roots: Iterable[MemoryRecord]) -> list[MemoryRecord] | None:
            """Return dependency-first additions for roots without mutating selection."""

            additions: list[MemoryRecord] = []
            visiting: set[str] = set()
            staged_ids = set(selected_ids)

            def visit(item: MemoryRecord) -> bool:
                if item.record_id in staged_ids:
                    return True
                if item.record_id in visiting:
                    return False
                visiting.add(item.record_id)
                if config.use_dependencies:
                    for dependency_id in item.requires:
                        dependency = eligible_by_id.get(dependency_id)
                        if dependency is None or not visit(dependency):
                            return False
                visiting.remove(item.record_id)
                staged_ids.add(item.record_id)
                additions.append(item)
                return True

            for root in roots:
                if not visit(root):
                    return None
            return additions

        def try_select(record: MemoryRecord, reason: str, limit: int | None = None) -> bool:
            nonlocal spent
            if record.record_id in selected_ids:
                mark_selected(record.record_id, reason)
                return True
            additions = selection_bundle((record,))
            if additions is None:
                decision_reasons[record.record_id].append("omitted:dependency_unavailable")
                return False
            proposed = selected + additions
            proposed_tokens = rendered_token_cost(
                proposed,
                policy_version=config.policy_version,
            )
            ceiling = (
                config.budget_tokens
                if limit is None
                else min(config.budget_tokens, base_tokens + limit)
            )
            if proposed_tokens > ceiling:
                decision_reasons[record.record_id].append("omitted:budget")
                if any(item.record_id != record.record_id for item in additions):
                    decision_reasons[record.record_id].append("omitted:dependency_budget")
                return False
            for addition in additions:
                selected.append(addition)
                selected_ids.add(addition.record_id)
                mark_selected(
                    addition.record_id,
                    reason if addition.record_id == record.record_id else "selected:required_link",
                )
            spent = proposed_tokens
            return True

        def try_select_conflict_pair(
            disputed: MemoryRecord,
            counterpart: MemoryRecord,
        ) -> bool:
            """Select a disputed/counterpart pair atomically before optional records."""

            nonlocal spent
            additions = selection_bundle((disputed, counterpart))
            if additions is None:
                decision_reasons[counterpart.record_id].append("omitted:dependency_unavailable")
                decision_reasons[counterpart.record_id].append(
                    "omitted:conflict_bundle_unavailable"
                )
                return False
            proposed = selected + additions
            proposed_tokens = rendered_token_cost(
                proposed,
                policy_version=config.policy_version,
            )
            if proposed_tokens > config.budget_tokens:
                decision_reasons[counterpart.record_id].append("omitted:budget")
                decision_reasons[counterpart.record_id].append("omitted:conflict_bundle_budget")
                return False
            for addition in additions:
                selected.append(addition)
                selected_ids.add(addition.record_id)
                if addition.record_id == disputed.record_id:
                    reason = "selected:disputed_bundle"
                elif addition.record_id == counterpart.record_id:
                    reason = "selected:conflict_counterpart"
                else:
                    reason = "selected:required_link"
                mark_selected(addition.record_id, reason)
            mark_selected(disputed.record_id, "selected:disputed_bundle")
            mark_selected(counterpart.record_id, "selected:conflict_counterpart")
            spent = proposed_tokens
            return True

        mandatory = sorted(
            (record for record in candidates if record.pinned),
            key=lambda record: (-scores[record.record_id].total, record.record_id),
        )
        for record in mandatory:
            if not try_select(record, "selected:pinned"):
                reasons = ", ".join(decision_reasons[record.record_id])
                raise ProtectedSelectionError(
                    f"protected record {record.record_id!r} could not be selected: {reasons}"
                )

        # Resolve live conflict pairs before ordinary lane/MMR selection can consume
        # capacity that would otherwise fit the disputed record and its counterpart.
        disputed_candidates = [
            record
            for record in candidates
            if record.state is RecordState.DISPUTED and record.conflicts_with
        ]
        for record in disputed_candidates:
            for counterpart_id in record.conflicts_with:
                counterpart = eligible_by_id.get(counterpart_id)
                if counterpart is not None:
                    try_select_conflict_pair(record, counterpart)

        def mmr_order(pool: list[MemoryRecord]) -> list[MemoryRecord]:
            if not config.use_diversity:
                return sorted(
                    pool,
                    key=lambda record: (-scores[record.record_id].total, record.record_id),
                )
            remaining = {record.record_id: record for record in pool}
            ordered: list[MemoryRecord] = []
            reference_tokens = [document_tokens[item.record_id] for item in selected]
            while remaining:
                choices: list[tuple[float, str, float, MemoryRecord]] = []
                for record in remaining.values():
                    redundancy = max(
                        (
                            jaccard(document_tokens[record.record_id], prior)
                            for prior in reference_tokens
                        ),
                        default=0.0,
                    )
                    diversity = 1.0 - redundancy
                    marginal = (
                        config.mmr_lambda * scores[record.record_id].total
                        + (1 - config.mmr_lambda) * diversity
                    )
                    choices.append((marginal, record.record_id, diversity, record))
                _, _, diversity, chosen = max(choices, key=lambda item: (item[0], item[1]))
                base = scores[chosen.record_id]
                scores[chosen.record_id] = ScoreBreakdown(
                    relevance=base.relevance,
                    rank_fusion=base.rank_fusion,
                    scope=base.scope,
                    continuity=base.continuity,
                    trust=base.trust,
                    recency=base.recency,
                    diversity=diversity,
                    total=base.total,
                )
                ordered.append(chosen)
                reference_tokens.append(document_tokens[chosen.record_id])
                del remaining[chosen.record_id]
            return ordered

        lane_limits = {
            "protected": int(usable_budget * config.protected_fraction),
            "continuity": int(
                usable_budget * (config.protected_fraction + config.continuity_fraction)
            ),
            "evidence": int(
                usable_budget
                * (
                    config.protected_fraction
                    + config.continuity_fraction
                    + config.evidence_fraction
                )
            ),
        }
        if config.use_lane_reservation:
            for lane in ("protected", "continuity", "evidence"):
                pool = [
                    record
                    for record in candidates
                    if record.kind in _LANES[lane] and record.record_id not in selected_ids
                ]
                for record in mmr_order(pool):
                    try_select(record, f"selected:lane:{lane}", lane_limits[lane])

        remaining = [record for record in candidates if record.record_id not in selected_ids]
        for record in mmr_order(remaining):
            try_select(record, "selected:shared_budget")

        decisions: list[SelectionDecision] = []
        for record in all_records:
            is_selected = record.record_id in selected_ids
            reasons = [
                reason
                for reason in decision_reasons[record.record_id]
                if not (
                    (is_selected and reason.startswith("omitted:"))
                    or (not is_selected and reason.startswith("selected:"))
                )
            ]
            if not reasons:
                reasons = ["selected:shared_budget" if is_selected else "omitted:low_rank"]
            decisions.append(
                SelectionDecision(
                    record_id=record.record_id,
                    selected=is_selected,
                    reason_codes=tuple(dict.fromkeys(reasons)),
                    token_cost=record.token_estimate,
                    score=scores.get(record.record_id),
                )
            )

        return SelectionPlan(
            selected=tuple(selected),
            decisions=tuple(decisions),
            budget_tokens=config.budget_tokens,
            selected_tokens=spent,
            policy_version=config.policy_version,
        )
