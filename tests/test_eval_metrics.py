from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acheon.evals.dataset import EvaluationCase  # noqa: E402
from acheon.evals.metrics import (  # noqa: E402
    aggregate_metrics,
    paired_bootstrap_delta,
    score_case,
)
from acheon.models import MemoryRecord  # noqa: E402


class EvaluationMetricTests(unittest.TestCase):
    def setUp(self) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        records = tuple(
            MemoryRecord(
                record_id=record_id,
                namespace="test",
                text=f"text {record_id}",
                created_at=now,
            )
            for record_id in ("relevant", "dependency", "current", "forbidden")
        )
        self.case = EvaluationCase(
            case_id="metric-case",
            scenario="mixed_history",
            namespace="test",
            query="query",
            scopes=("global",),
            as_of=now,
            budget_tokens=500,
            records=records,
            relevant_ids=frozenset(("relevant", "dependency", "current")),
            forbidden_ids=frozenset(("forbidden",)),
            dependency_ids=frozenset(("dependency",)),
            current_fact_ids=frozenset(("current",)),
        )

    def test_case_metrics_follow_declared_denominators(self) -> None:
        row = score_case(
            self.case,
            selected_ids=("relevant", "dependency", "forbidden"),
            selected_tokens=501,
            deterministic=True,
            latency_ms=2.5,
        )
        self.assertAlmostEqual(row.recall_at_budget, 2 / 3)
        self.assertAlmostEqual(row.precision, 2 / 3)
        self.assertEqual(row.forbidden_inclusion, 1.0)
        self.assertAlmostEqual(row.forbidden_selected_fraction, 1 / 3)
        self.assertEqual(row.dependency_recall, 1.0)
        self.assertEqual(row.current_fact_recall, 0.0)
        self.assertEqual(row.budget_violation, 1.0)

    def test_aggregate_reports_rates_and_latency_percentiles(self) -> None:
        first = score_case(
            self.case,
            selected_ids=("relevant",),
            selected_tokens=20,
            deterministic=True,
            latency_ms=1.0,
        )
        second = replace(first, case_id="metric-case-2", latency_ms=3.0, deterministic=0.0)
        aggregate = aggregate_metrics((first, second))
        self.assertEqual(aggregate["case_count"], 2)
        self.assertEqual(aggregate["determinism_rate"], 0.5)
        self.assertEqual(aggregate["latency_ms"]["p50"], 2.0)

    def test_paired_bootstrap_is_seeded_and_uses_paired_deltas(self) -> None:
        reference = score_case(
            self.case,
            selected_ids=("relevant", "dependency", "current"),
            selected_tokens=60,
            deterministic=True,
            latency_ms=1.0,
        )
        comparator = score_case(
            self.case,
            selected_ids=(),
            selected_tokens=0,
            deterministic=True,
            latency_ms=0.5,
        )
        first = paired_bootstrap_delta((reference,), (comparator,), seed=7, samples=100)
        second = paired_bootstrap_delta((reference,), (comparator,), seed=7, samples=100)
        self.assertEqual(first, second)
        self.assertEqual(first["recall_at_budget"]["estimate"], 1.0)
        self.assertEqual(first["recall_at_budget"]["ci_95"], [1.0, 1.0])
        self.assertEqual(first["forbidden_inclusion"]["direction"], "lower_is_better")

    def test_paired_bootstrap_rejects_unpaired_inputs(self) -> None:
        row = score_case(
            self.case,
            selected_ids=(),
            selected_tokens=0,
            deterministic=True,
            latency_ms=0.0,
        )
        with self.assertRaises(ValueError):
            paired_bootstrap_delta((row,), (replace(row, case_id="other"),), seed=1)


if __name__ == "__main__":
    unittest.main()
