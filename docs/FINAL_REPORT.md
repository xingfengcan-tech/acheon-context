# Acheon final engineering report

## Executive outcome

Acheon is a release-candidate Developer Tools project for OpenAI Build Week. It
implements a deterministic application-layer context compiler, versioned selective
memory store, inspectable selection trace, offline web demo, optional GPT-5.6 Sol
Responses API boundary, and a reproducible evaluation package.

The automated offline scope is complete, and one credentialed GPT-5.6 Sol smoke
test completed over public demo data. The source repository and release artifacts
are public. Legal eligibility confirmation, final Devpost submission, and YouTube
upload remain operator-gated steps and were not fabricated or bypassed.

## Delivered system

The public package contains:

- immutable typed records with namespace, scope, provenance, lifecycle, trust,
  dependencies, conflicts, expiry, and checksums;
- SQLite revisions with optimistic write checks, atomic supersession, revocation,
  full-revision integrity coverage, and a hash-chained activity log;
- hard lifecycle and scope gates, deterministic multi-rank candidate fusion,
  protected records, dependency closure, lane coverage, and diversity selection;
- a strict estimated-unit-budget canonical JSON context envelope with selected/omitted reason codes,
  packet digest, and audit receipt;
- an offline CLI and zero-build local web interface;
- a thin OpenAI Responses API adapter targeting `gpt-5.6-sol`, with dynamic history
  kept as user data, `store=False`, bounded timeout/retry behavior, and provider
  receipt fields;
- three equal-budget controls, six single-feature ablations, 2,000-sample paired
  bootstrap intervals, per-case results, and every structured failure;
- CI, diagrams, security guidance, a submission draft, a narrated demo script, and
  an allowlisted deterministic release archive builder.

## Offline evaluation

### Scope

The checked-in workload contains 240 fixed-seed synthetic record-selection cases:
six configurations, 40 cases per configuration, and 64 records per case. Each case
declares relevant, forbidden, dependency, and current-fact IDs. All systems receive
the same 640 estimated-token-unit packet budget and 124-unit empty-envelope cost. The
deterministic estimator is provider-independent and is not an exact GPT tokenizer.

This benchmark measures selection contracts. It does not call a language model and
does not measure generated-answer quality, general intelligence, provider context
window size, or permanent model memory.

### Absolute results

| System | Recall@budget | Precision | Forbidden inclusion | Dependency recall |
|---|---:|---:|---:|---:|
| Acheon full | 1.000 | 0.857 | 0.000 | 1.000 |
| Recent tail | 0.167 | 0.143 | 1.000 | 0.000 |
| Chronological prefix | 0.000 | 0.000 | 0.000 | 0.000 |
| Lexical top-k | 0.000 | 0.000 | 1.000 | 0.000 |

The full policy also records 1.000 current-fact recall, 0 budget violations, 1.000
determinism, and zero full-policy failure entries under the declared failure
categories. Its host-dependent final-packet selection latency was 55.23 ms mean and
68.43 ms p95 on Python 3.14 / Windows 11. The artifact includes 1,731 structured failure
entries across baselines and ablations rather than suppressing negative cases.

Paired Recall@budget improvements for full Acheon minus comparator were:

- recent tail: +0.833, 95% bootstrap interval [0.833, 0.833];
- chronological prefix: +1.000 [1.000, 1.000];
- lexical top-k: +1.000 [1.000, 1.000].

The intervals are unusually tight because cases share a transparent synthetic role
template. They should not be interpreted as uncertainty estimates for real-world
traffic.

### Ablation findings

| Disabled behavior | Recall delta, full minus ablation | 95% interval | Important secondary result |
|---|---:|---:|---|
| Lifecycle gate | +0.333 | [0.333, 0.333] | forbidden inclusion becomes 1.000 |
| Scope gate | +0.333 | [0.333, 0.333] | forbidden inclusion becomes 1.000 |
| Rank fusion | +0.000 | [0.000, 0.000] | no measured change on this workload |
| Diversity | +0.335 | [0.333, 0.337] | dependency recall becomes 0.000 |
| Dependency closure | +0.167 | [0.167, 0.167] | dependency recall becomes 0.000 |
| Lane reservation | +0.035 | [0.027, 0.044] | dependency recall remains 1.000 |

The zero rank-fusion result is retained because an honest evaluation must show which
parts were not demonstrated by the current generator.

## Integrity and safety validation

The regression suite covers record validation, atomic revision conflicts,
cross-namespace rollback, current and historical payload tampering, prevention of
post-tamper re-anchoring, namespace rerouting, deleted or malformed audit events,
lifecycle and scope gates, mutually exclusive final reason codes, protected candidate
handling, dependency closure, empty-envelope and selected-packet estimated budgets,
hostile record text as JSON
data, deterministic compilation, missing-key preview behavior, OpenAI request
shape, error redaction, security headers, static-path isolation, and complete local
HTTP flows.

The local audit chain is tamper-evident, not tamper-proof. Without an external
signed or append-only head, a privileged attacker can rewrite the database and
recompute local hashes or truncate a valid tail. The package states this limitation
explicitly.

## GPT-5.6 evidence status

The runtime integration is implemented, test-injected, and observed once through a
real GPT-5.6 Sol Responses API call over the repository's public seeded demo. The
machine-readable receipt is `artifacts/online/latest.json`: status `completed`,
returned model `gpt-5.6-sol`, 742 input / 382 output / 1,124 total tokens (55
reasoning tokens within output), 11,530.3 ms latency, provider request and response
IDs, packet digest, six selected record IDs, timestamp, and no failure.

This observation proves that the compiled packet reached the intended model and
that the adapter captured a provider receipt. It is one smoke test, not a
same-model raw-versus-Acheon experiment. Downstream answer-quality improvement,
real-workload generalization, expanded native context, and permanent model memory
remain **not evaluated**.

## Claim decision

The project demonstrates a large improvement over three simple controls on its
disclosed synthetic selection workload. It does **not** establish a universal,
paradigm-level, or model-internal improvement. Confirming that stronger claim would
require credentialed same-model answer evaluations, unseen real workloads,
independent replication, and outcome metrics beyond record selection.

## Build Week handoff

The best-fit category is **Developer Tools**. The English submission copy, demo
script, Codex-use record, architecture, methodology, limitations, and release
checklist are included. Remaining operator fields are marked `PENDING` rather than
invented.

The reviewed publication boundary is the allowlisted ZIP, not this development
repository's existing Git metadata. Create a fresh submission repository from the
archive; do not mirror or `push --all` the development repository.

Before submission, the operator must confirm legal eligibility, verify the recorded
Codex session ID, record and publish the prepared narrated YouTube demo under three
minutes, test all judge-access paths, and
submit before **2026-07-21 17:00 PDT / 2026-07-22 08:00 Asia/Shanghai**.

## Reproduction receipts

- Benchmark schema: `acheon.offline-selection-benchmark.v1`
- Benchmark report digest:
  `19744385e632ac547bdd6a1c2144bfc43addc2d8383a53e5996e888fa561d11e`
- Workload digest:
  `69095ac3c1115063e9f6a1e1f91bacce8793ad12aac2d8fbb5368026b441471d`
- Configuration digest:
  `72482accd7550338bb9ae3fce1867d1dcf281fe9cd847b1350b5629ed669e677`
- Live runtime receipt: `artifacts/online/latest.json`
- Live packet digest:
  `bb085270c45cdb5f378c7ce2233c243eca74b1b8bb6f6312f57757f3a52f934c`

Run from the repository root:

```powershell
python -m unittest discover -s tests -v
python -m acheon.evals.run --output artifacts/benchmark/latest.json
python scripts/generate_diagrams.py
python scripts/verify_release.py
python scripts/build_release.py
python scripts/verify_release.py --require-archive
```

Timing and the top-level report digest change across hosts because timing is part of
the report; selected IDs, absolute selection metrics, workload digest, and
configuration digest are deterministic for the fixed release input.

