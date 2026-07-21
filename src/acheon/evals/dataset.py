"""Fixed-seed synthetic long-history workload.

The workload tests context-selection contracts only.  Its labels are generated
from explicit scenario roles and are not observations of a language model.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..models import MemoryKind, MemoryRecord, RecordState, TrustClass
from ..rendering import rendered_token_cost

DEFAULT_SEED = 20_260_719
DEFAULT_CASES_PER_SCENARIO = 40
DEFAULT_HISTORY_SIZE = 64
AS_OF = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
POLICY_VERSION = "acheon-selector-v1"

SCENARIOS = (
    "lifecycle_churn",
    "scope_collision",
    "dependency_chain",
    "continuity_lanes",
    "redundant_evidence",
    "mixed_history",
)

_FACETS = (
    ("latency", "region"),
    ("schema", "migration"),
    ("quota", "tenant"),
    ("release", "rollback"),
    ("pricing", "currency"),
    ("policy", "retention"),
    ("build", "platform"),
    ("quality", "threshold"),
)


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    """One retrieval query and its role-derived gold labels."""

    case_id: str
    scenario: str
    namespace: str
    query: str
    scopes: tuple[str, ...]
    as_of: datetime
    budget_tokens: int
    records: tuple[MemoryRecord, ...]
    relevant_ids: frozenset[str]
    forbidden_ids: frozenset[str]
    dependency_ids: frozenset[str]
    current_fact_ids: frozenset[str]

    def __post_init__(self) -> None:
        known = {record.record_id for record in self.records}
        if self.scenario not in SCENARIOS:
            raise ValueError(f"unknown scenario: {self.scenario}")
        if len(known) != len(self.records):
            raise ValueError("record IDs must be unique within a case")
        for name in (
            "relevant_ids",
            "forbidden_ids",
            "dependency_ids",
            "current_fact_ids",
        ):
            values = getattr(self, name)
            if not values:
                raise ValueError(f"{name} cannot be empty")
            if not values <= known:
                raise ValueError(f"{name} contains unknown record IDs")
        if self.relevant_ids & self.forbidden_ids:
            raise ValueError("relevant and forbidden labels must be disjoint")
        if not self.dependency_ids <= self.relevant_ids:
            raise ValueError("dependency labels must also be relevant")
        if not self.current_fact_ids <= self.relevant_ids:
            raise ValueError("current-fact labels must also be relevant")
        if self.gold_packet_tokens > self.budget_tokens:
            raise ValueError("gold record packet cannot fit within the declared budget")

    @property
    def gold_packet_tokens(self) -> int:
        gold_records = [record for record in self.records if record.record_id in self.relevant_ids]
        return rendered_token_cost(gold_records, policy_version=POLICY_VERSION)

    def manifest(self) -> dict[str, object]:
        """Return labels and non-content metadata suitable for result JSON."""

        return {
            "case_id": self.case_id,
            "scenario": self.scenario,
            "namespace": self.namespace,
            "query": self.query,
            "scopes": list(self.scopes),
            "as_of": self.as_of.isoformat(),
            "budget_tokens": self.budget_tokens,
            "history_records": len(self.records),
            "gold_packet_tokens": self.gold_packet_tokens,
            "gold": {
                "relevant_ids": sorted(self.relevant_ids),
                "forbidden_ids": sorted(self.forbidden_ids),
                "dependency_ids": sorted(self.dependency_ids),
                "current_fact_ids": sorted(self.current_fact_ids),
            },
        }


def _case_seed(seed: int, scenario_index: int, case_index: int) -> int:
    # Avoid hash(), whose process randomization would weaken reproducibility.
    return seed * 1_000_003 + scenario_index * 10_007 + case_index * 101


def _build_case(
    *,
    seed: int,
    scenario: str,
    scenario_index: int,
    case_index: int,
    history_size: int,
) -> EvaluationCase:
    if history_size < 32:
        raise ValueError("history_size must be at least 32")

    rng = random.Random(_case_seed(seed, scenario_index, case_index))
    case_id = f"{scenario}-{case_index:03d}"
    namespace = f"offline-{scenario}"
    scope = f"project-{case_index % 9}"
    other_scope = f"project-{(case_index + 4) % 9}"
    facet_a, facet_b = _FACETS[(case_index + scenario_index) % len(_FACETS)]
    key = f"{scenario_index:02d}k{case_index:03d}"
    value = f"value-{rng.randrange(10_000, 99_999)}"
    query = (
        f"Prepare the current {key} {facet_a} {facet_b} decision artifact, "
        "including constraints and verified support."
    )

    records: list[MemoryRecord] = []
    relevant: set[str] = set()
    forbidden: set[str] = set()
    dependencies: set[str] = set()
    current_facts: set[str] = set()

    def add(
        role: str,
        text: str,
        *,
        kind: MemoryKind = MemoryKind.FACT,
        state: RecordState = RecordState.ACTIVE,
        scopes: tuple[str, ...] = (scope,),
        age_days: float,
        topic: str = "",
        tags: tuple[str, ...] = (),
        trust: TrustClass = TrustClass.OBSERVED,
        confidence: float = 0.8,
        valid_for_days: float | None = None,
        requires: tuple[str, ...] = (),
        pinned: bool = False,
    ) -> str:
        record_id = f"{scenario_index:02d}-{case_index:03d}-{role}"
        created_at = AS_OF - timedelta(days=age_days)
        valid_until = (
            created_at + timedelta(days=valid_for_days) if valid_for_days is not None else None
        )
        records.append(
            MemoryRecord(
                record_id=record_id,
                namespace=namespace,
                text=text,
                kind=kind,
                state=state,
                topic=topic,
                scopes=scopes,
                tags=tags,
                source="offline-synthetic",
                trust=trust,
                confidence=confidence,
                created_at=created_at,
                valid_until=valid_until,
                requires=requires,
                pinned=pinned,
                metadata={"synthetic_role": role, "scenario": scenario},
            )
        )
        return record_id

    instruction_id = add(
        "instruction",
        "Preserve the accepted source boundary and cite evidence in the final response.",
        kind=MemoryKind.INSTRUCTION,
        scopes=("global",),
        age_days=220,
        topic="operating-constraint",
        tags=("operating-rule",),
        trust=TrustClass.USER_CONFIRMED,
        confidence=1.0,
    )
    decision_id = add(
        "decision",
        f"The active decision for {key} requires the {facet_a} review before release.",
        kind=MemoryKind.DECISION,
        age_days=170,
        topic=key,
        tags=("decision", facet_a),
        trust=TrustClass.USER_CONFIRMED,
        confidence=0.98,
    )
    dependency_id = add(
        "dependency",
        f"Ledger entry {value} establishes the accepted source boundary.",
        kind=MemoryKind.EVIDENCE,
        age_days=130,
        topic=f"ledger-{value}",
        tags=("ledger", "origin"),
        trust=TrustClass.VERIFIED,
        confidence=0.97,
    )
    artifact_id = add(
        "artifact",
        f"The {key} {facet_b} artifact uses support ledger {value} and the active decision.",
        kind=MemoryKind.ARTIFACT,
        age_days=90,
        topic=key,
        tags=("artifact", facet_b),
        trust=TrustClass.VERIFIED,
        confidence=0.96,
        requires=(dependency_id,),
    )
    current_id = add(
        "current",
        f"Current {key} {facet_a} setting is {value}; this replaces the earlier setting.",
        kind=MemoryKind.FACT,
        age_days=5,
        topic=key,
        tags=("current", facet_a),
        trust=TrustClass.VERIFIED,
        confidence=0.99,
    )
    breadth_id = add(
        "breadth",
        f"Independent verified {facet_b} evidence for {key} covers the secondary requirement.",
        kind=MemoryKind.EVIDENCE,
        age_days=60,
        topic=key,
        tags=("verified", facet_b),
        trust=TrustClass.VERIFIED,
        confidence=0.95,
    )
    relevant.update(
        {instruction_id, decision_id, dependency_id, artifact_id, current_id, breadth_id}
    )
    dependencies.add(dependency_id)
    current_facts.add(current_id)

    stale_id = add(
        "stale",
        f"Current {key} {facet_a} {facet_b} decision artifact uses obsolete-old-value.",
        kind=MemoryKind.FACT,
        state=RecordState.SUPERSEDED,
        age_days=250,
        topic=key,
        tags=("current", "decision", "artifact"),
    )
    revoked_id = add(
        "revoked",
        f"Current {key} {facet_a} constraint says to use revoked-value immediately.",
        kind=MemoryKind.INSTRUCTION,
        state=RecordState.REVOKED,
        age_days=1,
        topic=key,
        tags=("current", "constraints"),
    )
    expired_id = add(
        "expired",
        f"Verified support for current {key} {facet_b} decision was temporary-expired-value.",
        kind=MemoryKind.EVIDENCE,
        age_days=40,
        valid_for_days=10,
        topic=key,
        tags=("verified", "support", "decision"),
    )
    cross_scope_id = add(
        "cross-scope",
        f"Current {key} {facet_a} {facet_b} decision artifact is wrong-scope-value.",
        kind=MemoryKind.DECISION,
        scopes=(other_scope,),
        age_days=0.2,
        topic=key,
        tags=("current", "decision", "artifact"),
        trust=TrustClass.USER_CONFIRMED,
        confidence=1.0,
    )
    forbidden.update({stale_id, revoked_id, expired_id, cross_scope_id})

    scenario_bias = {
        "lifecycle_churn": (9, 2),
        "scope_collision": (7, 4),
        "dependency_chain": (5, 2),
        "continuity_lanes": (10, 2),
        "redundant_evidence": (14, 1),
        "mixed_history": (7, 2),
    }[scenario]
    redundant_count, recent_noise_count = scenario_bias
    decoy_index = 0
    while len(records) < history_size:
        is_redundant = decoy_index < redundant_count
        is_recent = decoy_index < recent_noise_count
        decoy_facet = facet_a if decoy_index % 2 == 0 else facet_b
        if is_redundant:
            text = (
                f"Draft {key} {decoy_facet} review repeats preliminary artifact discussion "
                f"batch-{decoy_index % 3}; it is not verified support."
            )
            tags = (decoy_facet, "draft")
            topic = f"draft-{key}"
        else:
            noise_key = f"noise-{scenario_index}-{case_index}-{decoy_index}"
            text = (
                f"Unrelated historical note {noise_key} covers archive housekeeping "
                f"and routine batch {rng.randrange(1_000)}."
            )
            tags = ("archive", f"batch-{decoy_index % 11}")
            topic = noise_key
        age = (
            0.4 + decoy_index * 0.03
            if is_recent
            else float(rng.randrange(8, 420)) + decoy_index / 1_000
        )
        add(
            f"decoy-{decoy_index:02d}",
            text,
            kind=(MemoryKind.FACT if decoy_index % 3 else MemoryKind.EVENT),
            age_days=age,
            topic=topic,
            tags=tags,
            trust=TrustClass.INFERRED if is_redundant else TrustClass.OBSERVED,
            confidence=0.45 if is_redundant else 0.7,
        )
        decoy_index += 1

    # Stable shuffling makes caller order uninformative while preserving all
    # chronology in the records themselves.
    rng.shuffle(records)
    return EvaluationCase(
        case_id=case_id,
        scenario=scenario,
        namespace=namespace,
        query=query,
        scopes=(scope,),
        as_of=AS_OF,
        budget_tokens=640,
        records=tuple(records),
        relevant_ids=frozenset(relevant),
        forbidden_ids=frozenset(forbidden),
        dependency_ids=frozenset(dependencies),
        current_fact_ids=frozenset(current_facts),
    )


def generate_workload(
    *,
    seed: int = DEFAULT_SEED,
    cases_per_scenario: int = DEFAULT_CASES_PER_SCENARIO,
    history_size: int = DEFAULT_HISTORY_SIZE,
) -> tuple[EvaluationCase, ...]:
    """Generate the reproducible default 240-case workload."""

    if cases_per_scenario < 1:
        raise ValueError("cases_per_scenario must be positive")
    return tuple(
        _build_case(
            seed=seed,
            scenario=scenario,
            scenario_index=scenario_index,
            case_index=case_index,
            history_size=history_size,
        )
        for scenario_index, scenario in enumerate(SCENARIOS)
        for case_index in range(cases_per_scenario)
    )
