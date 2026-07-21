"""Command-line entry point for the deterministic offline benchmark."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .benchmark import REFERENCE_SYSTEM, run_benchmark
from .dataset import (
    DEFAULT_CASES_PER_SCENARIO,
    DEFAULT_HISTORY_SIZE,
    DEFAULT_SEED,
    generate_workload,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/benchmark/latest.json"),
        help="machine-readable JSON output path",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--cases-per-scenario",
        type=int,
        default=DEFAULT_CASES_PER_SCENARIO,
    )
    parser.add_argument("--history-size", type=int, default=DEFAULT_HISTORY_SIZE)
    parser.add_argument("--bootstrap-samples", type=int, default=2_000)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workload = generate_workload(
        seed=args.seed,
        cases_per_scenario=args.cases_per_scenario,
        history_size=args.history_size,
    )
    report = run_benchmark(
        workload,
        seed=args.seed,
        bootstrap_samples=args.bootstrap_samples,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    aggregate = report["systems"][REFERENCE_SYSTEM]["aggregate"]
    print(
        f"wrote {args.output} | cases={aggregate['case_count']} "
        f"recall={aggregate['recall_at_budget']:.3f} "
        f"precision={aggregate['precision']:.3f} "
        f"forbidden={aggregate['forbidden_inclusion_rate']:.3f}"
    )
    print("offline synthetic selection benchmark; no language-model capability claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
