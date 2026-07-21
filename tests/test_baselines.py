from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acheon.baselines import (  # noqa: E402
    PACKET_OVERHEAD_TOKENS,
    chronological_prefix,
    lexical_topk,
    recent_tail,
    usable_content_budget,
)
from acheon.models import MemoryRecord  # noqa: E402
from acheon.rendering import rendered_token_cost  # noqa: E402


class BaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        moment = datetime(2026, 1, 1, tzinfo=UTC)
        self.records = tuple(
            MemoryRecord(
                record_id=f"r{index}",
                namespace="test",
                text=text,
                created_at=moment + timedelta(days=index),
            )
            for index, text in enumerate(("alpha", "target alpha", "omega"))
        )
        self.budget = rendered_token_cost(
            self.records[:2],
            policy_version="acheon-selector-v1",
        )

    def test_usable_budget_reserves_identical_packet_overhead(self) -> None:
        self.assertEqual(usable_content_budget(PACKET_OVERHEAD_TOKENS + 17), 17)
        self.assertEqual(usable_content_budget(12), 0)
        with self.assertRaises(ValueError):
            usable_content_budget(-1)

    def test_chronological_prefix_is_oldest_first_and_bounded(self) -> None:
        result = chronological_prefix(
            reversed(self.records), query="ignored", budget_tokens=self.budget
        )
        self.assertEqual(result.selected_ids, ("r0", "r1"))
        self.assertLessEqual(result.selected_tokens, self.budget)

    def test_recent_tail_is_newest_first_and_bounded(self) -> None:
        result = recent_tail(self.records, query="ignored", budget_tokens=self.budget)
        self.assertEqual(result.selected_ids, ("r2", "r1"))
        self.assertLessEqual(result.selected_tokens, self.budget)

    def test_lexical_topk_prefers_overlap_and_is_deterministic(self) -> None:
        first = lexical_topk(self.records, query="target", budget_tokens=self.budget)
        second = lexical_topk(reversed(self.records), query="target", budget_tokens=self.budget)
        self.assertEqual(first.selected_ids[0], "r1")
        self.assertEqual(first.selected_ids, second.selected_ids)
        self.assertEqual(first.selected_tokens, second.selected_tokens)

    def test_prefix_stops_when_next_ranked_record_does_not_fit(self) -> None:
        result = recent_tail(
            (self.records[0],),
            query="ignored",
            budget_tokens=PACKET_OVERHEAD_TOKENS,
        )
        self.assertEqual(result.selected_ids, ())
        self.assertEqual(result.selected_tokens, PACKET_OVERHEAD_TOKENS)


if __name__ == "__main__":
    unittest.main()
