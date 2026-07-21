"""Metrics and paired bootstrap intervals for the offline workload."""

from __future__ import annotations

import math
import random
import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass

from .dataset import EvaluationCase

BOOTSTRAP_METRICS = (
    "recall_at_budget",
    "precision",
    "forbidden_inclusion",
    "dependency_recall",
    "current_fact_recall",
    "budget_violation",
    "deterministic",
)

METRIC_DIRECTIONS = {
    "recall_at_budget": "higher_is_better",
    "precision": "higher_is_better",
    "forbidden_inclusion": "lower_is_better",
    "forbidden_selected_fraction": "lower_is_better",
    "dependency_recall": "higher_is_better",
    "current_fact_recall": "higher_is_better",
    "budget_violation": "lower_is_better",
    "deterministic": "higher_is_better",
}


@dataclass(frozen=True, slots=True)
class CaseMetrics:
    case_id: str
    scenario: str
    selected_ids: tuple[str, ...]
    selected_tokens: int
    recall_at_budget: float
    precision: float
    forbidden_inclusion: float
    forbidden_selected_fraction: float
    dependency_recall: float
    current_fact_recall: float
    budget_violation: float
    deterministic: float
    latency_ms: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _recall(selected: set[str], gold: frozenset[str]) -> float:
    return len(selected & gold) / len(gold)


def score_case(
    case: EvaluationCase,
    *,
    selected_ids: Iterable[str],
    selected_tokens: int,
    deterministic: bool,
    latency_ms: float,
) -> CaseMetrics:
    """Score one system output against explicit record-role labels."""

    ordered_ids = tuple(selected_ids)
    selected = set(ordered_ids)
    relevant_selected = len(selected & case.relevant_ids)
    forbidden_selected = len(selected & case.forbidden_ids)
    return CaseMetrics(
        case_id=case.case_id,
        scenario=case.scenario,
        selected_ids=ordered_ids,
        selected_tokens=selected_tokens,
        recall_at_budget=_recall(selected, case.relevant_ids),
        precision=(relevant_selected / len(selected)) if selected else 0.0,
        forbidden_inclusion=float(forbidden_selected > 0),
        forbidden_selected_fraction=(forbidden_selected / len(selected)) if selected else 0.0,
        dependency_recall=_recall(selected, case.dependency_ids),
        current_fact_recall=_recall(selected, case.current_fact_ids),
        budget_violation=float(selected_tokens > case.budget_tokens),
        deterministic=float(deterministic),
        latency_ms=latency_ms,
    )


def _percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("cannot take a percentile of an empty sequence")
    if not 0 <= probability <= 1:
        raise ValueError("probability must be in [0, 1]")
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def aggregate_metrics(rows: Sequence[CaseMetrics]) -> dict[str, object]:
    if not rows:
        raise ValueError("at least one case metric is required")

    def mean(name: str) -> float:
        return statistics.fmean(float(getattr(row, name)) for row in rows)

    latencies = [row.latency_ms for row in rows]
    selected_tokens = [row.selected_tokens for row in rows]
    return {
        "case_count": len(rows),
        "recall_at_budget": mean("recall_at_budget"),
        "precision": mean("precision"),
        "forbidden_inclusion_rate": mean("forbidden_inclusion"),
        "forbidden_selected_fraction": mean("forbidden_selected_fraction"),
        "dependency_recall": mean("dependency_recall"),
        "current_fact_recall": mean("current_fact_recall"),
        "budget_violation_rate": mean("budget_violation"),
        "determinism_rate": mean("deterministic"),
        "selected_tokens": {
            "mean": statistics.fmean(selected_tokens),
            "max": max(selected_tokens),
        },
        "latency_ms": {
            "mean": statistics.fmean(latencies),
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
            "max": max(latencies),
        },
    }


def paired_bootstrap_delta(
    reference: Sequence[CaseMetrics],
    comparator: Sequence[CaseMetrics],
    *,
    seed: int,
    samples: int = 2_000,
) -> dict[str, dict[str, object]]:
    """Return paired percentile CIs for ``reference - comparator`` means."""

    if samples < 100:
        raise ValueError("samples must be at least 100")
    reference_by_id = {row.case_id: row for row in reference}
    comparator_by_id = {row.case_id: row for row in comparator}
    if reference_by_id.keys() != comparator_by_id.keys():
        raise ValueError("paired inputs must contain the same case IDs")
    case_ids = sorted(reference_by_id)
    if not case_ids:
        raise ValueError("paired inputs cannot be empty")

    rng = random.Random(seed)
    deltas = {
        metric: [
            float(getattr(reference_by_id[case_id], metric))
            - float(getattr(comparator_by_id[case_id], metric))
            for case_id in case_ids
        ]
        for metric in BOOTSTRAP_METRICS
    }
    distributions: dict[str, list[float]] = {metric: [] for metric in BOOTSTRAP_METRICS}
    case_count = len(case_ids)
    for _ in range(samples):
        indices = [rng.randrange(case_count) for _ in range(case_count)]
        for metric, paired_deltas in deltas.items():
            distributions[metric].append(
                statistics.fmean(paired_deltas[index] for index in indices)
            )

    return {
        metric: {
            "estimate": statistics.fmean(paired_deltas),
            "ci_95": [
                _percentile(distributions[metric], 0.025),
                _percentile(distributions[metric], 0.975),
            ],
            "contrast": "reference_minus_comparator",
            "direction": METRIC_DIRECTIONS[metric],
            "samples": samples,
        }
        for metric, paired_deltas in deltas.items()
    }


def group_by_scenario(rows: Iterable[CaseMetrics]) -> Mapping[str, tuple[CaseMetrics, ...]]:
    grouped: dict[str, list[CaseMetrics]] = {}
    for row in rows:
        grouped.setdefault(row.scenario, []).append(row)
    return {name: tuple(values) for name, values in sorted(grouped.items())}
