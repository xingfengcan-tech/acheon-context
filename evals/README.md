# Offline selection benchmark

This benchmark is a fixed-seed synthetic workload for context-record selection.
It evaluates deterministic orchestration contracts; it does not call a language
model and does not measure general model intelligence, answer quality, provider
context-window size, or permanent model memory.

Run the release-sized workload from the repository root:

```powershell
$benchmarkCheck = Join-Path $env:TEMP "acheon-benchmark-check.json"
python -m acheon.evals.run --output $benchmarkCheck
python scripts/verify_release.py --compare-benchmark $benchmarkCheck
```

The default generator creates 240 cases across six synthetic configurations, with 64 historical
records per case. Every case carries explicit gold sets for relevant records,
forbidden records, dependency records, and current facts. The reference policy,
three budget-matched controls, and six single-feature ablations receive the same
final canonical estimated-unit context budget using the same renderer and
provider-independent estimator.

The JSON report includes per-case selections, aggregate and per-scenario metrics,
paired seeded bootstrap 95% intervals, a structured failure list, workload labels,
and a prominent evidence boundary. Latency is wall-clock diagnostic data and will
vary by host; selected record IDs remain deterministic.
