"""Offline benchmark orchestration and machine-readable reporting."""

from __future__ import annotations

import platform
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from typing import Any

from ..audit import digest_json
from ..baselines import BASELINES, PACKET_OVERHEAD_TOKENS, BaselineSelection
from ..compiler import ContextCompiler
from ..models import CompileConfig
from .dataset import DEFAULT_SEED, EvaluationCase, generate_workload
from .metrics import (
    CaseMetrics,
    aggregate_metrics,
    group_by_scenario,
    paired_bootstrap_delta,
    score_case,
)

REFERENCE_SYSTEM = "acheon_full"

ABLATION_FLAGS = {
    "ablation_no_lifecycle": "use_lifecycle_filter",
    "ablation_no_scope": "use_scope_filter",
    "ablation_no_rank_fusion": "use_rank_fusion",
    "ablation_no_diversity": "use_diversity",
    "ablation_no_dependencies": "use_dependencies",
    "ablation_no_lane_reservation": "use_lane_reservation",
}


@dataclass(frozen=True, slots=True)
class _Selection:
    selected_ids: tuple[str, ...]
    selected_tokens: int


@dataclass(frozen=True, slots=True)
class _System:
    name: str
    kind: str
    description: str
    select: Callable[[EvaluationCase], _Selection]


@dataclass(frozen=True, slots=True)
class _CaseCompilationSnapshot:
    records: tuple[Any, ...]
    namespace: str
    state_hash: str

    def record_activity(self, *, payload: dict[str, Any]) -> Any:
        event_hash = digest_json(
            {"action": "context.compile", "namespace": self.namespace, "payload": payload}
        )
        return type("BenchmarkEvent", (), {"event_hash": event_hash})()


@dataclass(frozen=True, slots=True)
class _CaseStore:
    records: tuple[Any, ...]

    def current_records(self, namespace: str) -> tuple[Any, ...]:
        return tuple(record for record in self.records if record.namespace == namespace)

    @contextmanager
    def compilation_snapshot(self, namespace: str) -> Iterator[_CaseCompilationSnapshot]:
        records = self.current_records(namespace)
        yield _CaseCompilationSnapshot(
            records=records,
            namespace=namespace,
            state_hash=digest_json([record.checksum for record in records]),
        )

    def record_activity(
        self,
        *,
        action: str,
        namespace: str,
        payload: dict[str, Any],
    ) -> Any:
        event_hash = digest_json({"action": action, "namespace": namespace, "payload": payload})
        return type("BenchmarkEvent", (), {"event_hash": event_hash})()


def _baseline_system(name: str) -> _System:
    baseline = BASELINES[name]

    def select(case: EvaluationCase) -> _Selection:
        result: BaselineSelection = baseline(
            case.records,
            query=case.query,
            budget_tokens=case.budget_tokens,
        )
        return _Selection(result.selected_ids, result.selected_tokens)

    descriptions = {
        "recent_tail": "Newest-first raw history truncation.",
        "chronological_prefix": "Oldest-first raw history truncation.",
        "lexical_topk": "Bag-of-words overlap ranking over raw history.",
    }
    return _System(name=name, kind="baseline", description=descriptions[name], select=select)


def _selector_system(name: str, disabled_flag: str | None = None) -> _System:
    def select(case: EvaluationCase) -> _Selection:
        config = CompileConfig(budget_tokens=case.budget_tokens)
        if disabled_flag is not None:
            config = replace(config, **{disabled_flag: False})
        packet = ContextCompiler(_CaseStore(case.records), config).compile(
            query=case.query,
            namespace=case.namespace,
            scopes=case.scopes,
            as_of=case.as_of,
        )
        return _Selection(
            packet.selected_ids,
            packet.used_tokens,
        )

    if disabled_flag is None:
        description = "Complete deterministic Acheon selection policy."
        kind = "reference"
    else:
        description = f"Acheon policy with {disabled_flag} disabled."
        kind = "ablation"
    return _System(name=name, kind=kind, description=description, select=select)


def benchmark_systems() -> tuple[_System, ...]:
    """Return reference, controls, and all required single-feature ablations."""

    return (
        _selector_system(REFERENCE_SYSTEM),
        *(_baseline_system(name) for name in BASELINES),
        *(_selector_system(name, disabled_flag) for name, disabled_flag in ABLATION_FLAGS.items()),
    )


def _evaluate_system(
    system: _System,
    cases: Sequence[EvaluationCase],
) -> tuple[CaseMetrics, ...]:
    rows: list[CaseMetrics] = []
    for case in cases:
        started = time.perf_counter_ns()
        first = system.select(case)
        latency_ms = (time.perf_counter_ns() - started) / 1_000_000
        second = system.select(case)
        deterministic = first == second
        rows.append(
            score_case(
                case,
                selected_ids=first.selected_ids,
                selected_tokens=first.selected_tokens,
                deterministic=deterministic,
                latency_ms=latency_ms,
            )
        )
    return tuple(rows)


def _failures(
    system_name: str,
    rows: Sequence[CaseMetrics],
    cases_by_id: dict[str, EvaluationCase],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in rows:
        case = cases_by_id[row.case_id]
        selected = set(row.selected_ids)
        categories: list[str] = []
        missed_relevant = sorted(case.relevant_ids - selected)
        forbidden_included = sorted(case.forbidden_ids & selected)
        missing_dependencies = sorted(case.dependency_ids - selected)
        missing_current_facts = sorted(case.current_fact_ids - selected)
        if missed_relevant:
            categories.append("missed_relevant")
        if forbidden_included:
            categories.append("forbidden_included")
        if missing_dependencies:
            categories.append("missing_dependency")
        if missing_current_facts:
            categories.append("missing_current_fact")
        if row.budget_violation:
            categories.append("budget_violation")
        if not row.deterministic:
            categories.append("nondeterministic")
        if categories:
            failures.append(
                {
                    "system": system_name,
                    "case_id": row.case_id,
                    "scenario": row.scenario,
                    "categories": categories,
                    "missed_relevant_ids": missed_relevant,
                    "forbidden_included_ids": forbidden_included,
                    "missing_dependency_ids": missing_dependencies,
                    "missing_current_fact_ids": missing_current_facts,
                    "selected_tokens": row.selected_tokens,
                    "budget_tokens": case.budget_tokens,
                }
            )
    return failures


def run_benchmark(
    cases: Sequence[EvaluationCase] | None = None,
    *,
    seed: int = DEFAULT_SEED,
    bootstrap_samples: int = 2_000,
) -> dict[str, Any]:
    """Run the fixed offline benchmark and return a JSON-safe report."""

    workload = tuple(cases) if cases is not None else generate_workload(seed=seed)
    if not workload:
        raise ValueError("benchmark workload cannot be empty")
    case_ids = [case.case_id for case in workload]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("benchmark case IDs must be unique")

    started = time.perf_counter()
    systems = benchmark_systems()
    rows_by_system = {system.name: _evaluate_system(system, workload) for system in systems}
    reference_rows = rows_by_system[REFERENCE_SYSTEM]
    system_payload: dict[str, Any] = {}
    failures: list[dict[str, Any]] = []
    cases_by_id = {case.case_id: case for case in workload}
    for system in systems:
        rows = rows_by_system[system.name]
        grouped = group_by_scenario(rows)
        system_payload[system.name] = {
            "kind": system.kind,
            "description": system.description,
            "aggregate": aggregate_metrics(rows),
            "by_scenario": {
                scenario: aggregate_metrics(scenario_rows)
                for scenario, scenario_rows in grouped.items()
            },
            "cases": [row.to_dict() for row in rows],
        }
        failures.extend(_failures(system.name, rows, cases_by_id))

    comparisons = {
        system.name: paired_bootstrap_delta(
            reference_rows,
            rows_by_system[system.name],
            seed=seed + index * 65_537,
            samples=bootstrap_samples,
        )
        for index, system in enumerate(systems, start=1)
        if system.name != REFERENCE_SYSTEM
    }
    elapsed_ms = (time.perf_counter() - started) * 1_000
    workload_manifest = [case.manifest() for case in workload]
    selector_configuration = asdict(CompileConfig())
    selector_configuration["budget_tokens"] = {
        "source": "workload",
        "values": sorted({case.budget_tokens for case in workload}),
    }
    configuration = {
        "selector": selector_configuration,
        "baselines": sorted(BASELINES),
        "ablations": dict(sorted(ABLATION_FLAGS.items())),
        "packet_overhead_tokens": PACKET_OVERHEAD_TOKENS,
    }
    report = {
        "schema_version": "acheon.offline-selection-benchmark.v1",
        "evidence_boundary": {
            "workload": "fixed-seed synthetic long-history record selection",
            "measures": "orchestration retrieval contracts under explicit gold labels",
            "does_not_measure": [
                "general language-model intelligence",
                "provider context-window size",
                "permanent model memory",
                "quality of generated answers",
            ],
            "claim_rule": (
                "Results apply only to this synthetic offline workload and must not be "
                "presented as observed model-capability gains."
            ),
        },
        "reproducibility": {
            "seed": seed,
            "case_count": len(workload),
            "scenario_count": len({case.scenario for case in workload}),
            "history_records_min": min(len(case.records) for case in workload),
            "history_records_max": max(len(case.records) for case in workload),
            "bootstrap_samples": bootstrap_samples,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "implementation": sys.implementation.name,
            "workload_digest": digest_json(workload_manifest),
            "configuration_digest": digest_json(configuration),
            "timing_note": (
                "Wall-clock latency is environment-dependent; selection outputs are fixed."
            ),
        },
        "metric_definitions": {
            "recall_at_budget": (
                "Mean fraction of gold-relevant IDs selected under the content budget."
            ),
            "precision": "Mean fraction of selected IDs that are gold-relevant.",
            "forbidden_inclusion_rate": "Fraction of cases selecting at least one forbidden ID.",
            "forbidden_selected_fraction": "Mean selected-set fraction carrying a forbidden label.",
            "dependency_recall": "Mean fraction of required dependency IDs selected.",
            "current_fact_recall": "Mean fraction of current-fact IDs selected.",
            "budget_violation_rate": (
                "Fraction whose final canonical context estimate exceeds budget_tokens."
            ),
            "determinism_rate": (
                "Fraction whose ordered IDs and token count match an immediate rerun."
            ),
            "paired_ci": (
                "Seeded paired percentile bootstrap 95% interval for reference minus comparator."
            ),
        },
        "configuration": configuration,
        "workload": workload_manifest,
        "systems": system_payload,
        "paired_bootstrap_95": comparisons,
        "failures": failures,
        "runtime_ms": elapsed_ms,
    }
    report["report_digest"] = digest_json(report)
    return report
