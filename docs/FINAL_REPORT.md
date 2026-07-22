# Acheon final engineering report

## Executive outcome

Acheon is a release-ready open-source research alpha for deterministic application-
layer context governance. It includes a versioned selective-memory store,
inspectable selection trace, offline web demo, optional GPT-5.6 Sol Responses API
boundary, and reproducible offline and model-behavior evaluation packages.

The automated offline scope is complete. One credentialed GPT-5.6 Sol adapter smoke
test and one standalone 24-sample context-integrity observation completed over
public synthetic data. The 2026 OpenAI Build Week deadline passed before submission,
so the project is not represented as prize-eligible; the active handoff instead
targets OpenAI Showcase, OpenAI Evals, and Developer Community review.

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
- a 24-sample, eight-category OpenAI Evals proposal with 16 labeled grader checks
  and a credential-free aggregate online receipt;
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
categories. Host-dependent final-packet selection timing is recorded in the JSON
artifact and is not treated as a portable quality claim. The artifact includes 1,731 structured failure
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
same-model raw-versus-Acheon experiment.

A separate direct Responses API run evaluated GPT-5.6 Sol on the 24 hand-authored
Long-Horizon Context Integrity cases. The same model generated and graded answers;
the labeled grader meta-eval was 16/16, and the primary automated result was 23/24
with no invalid grader output. `lhci-016` was the only failure. A separate
human-inspected reproduction remained safe and useful but omitted the required
version `6.2.1` and issue identifier `BUG-731`, confirming the eval captures a real
traceability omission. The public synthetic inputs are retained in the Eval dataset;
model completion text, assembled grader payloads, and provider request IDs were not
retained.

This standalone run does not contain an Acheon condition, uses one repetition and
a same-model grader, and does not preserve the original failed answer for human
inspection. It therefore supports the usefulness of the public Eval, not an
Acheon-attributable downstream improvement. Real-workload generalization, expanded
native context, and permanent model memory remain **not evaluated**.

## Claim decision

The project demonstrates a large improvement over three simple controls on its
disclosed synthetic selection workload and supplies one observed model-behavior
failure for a separate public Eval. It does **not** establish an Acheon-attributable,
universal, paradigm-level, or model-internal improvement. Confirming that stronger
claim requires same-model equal-token Acheon-versus-baseline evaluations, unseen
real workloads, independent replication, and outcome metrics beyond record
selection.

## OpenAI contribution handoff

OpenAI Build Week closed on **2026-07-21 17:00 PDT** and the Devpost challenge is in
judging. Acheon was not submitted before the deadline, and no late-submission claim
is made. The historical Build Week draft and demo script remain as provenance.

The active, reviewed package is `contributions/openai/`: Showcase field copy,
OpenAI Evals registry files, a Developer Community post, eight sanitized feedback
cases, a publication boundary, and fail-closed validation. Identity, authorship and
content rights, program-agreement acceptance, eval-data licensing, community
account identity, organization data-sharing choices, and final external submission
remain operator decisions rather than fabricated automation.

## Reproduction receipts

- Benchmark schema: `acheon.offline-selection-benchmark.v1`
- Benchmark report digest:
  `f7f41fda9743fef6ff7d75c8fd3e13d6cc48e5a40e56d535c1b328616bf10019`
- Workload digest:
  `69095ac3c1115063e9f6a1e1f91bacce8793ad12aac2d8fbb5368026b441471d`
- Configuration digest:
  `72482accd7550338bb9ae3fce1867d1dcf281fe9cd847b1350b5629ed669e677`
- Live runtime receipt: `artifacts/online/latest.json`
- Live packet digest:
  `bb085270c45cdb5f378c7ce2233c243eca74b1b8bb6f6312f57757f3a52f934c`
- Context-integrity online receipt:
  `artifacts/online/context-integrity-latest.json`
- Context-integrity report digest:
  `da85284481b36ff4875fafece727849f7cbd9fd7c07b856f47a5bf5413699def`
- Human-reviewed failure reproduction:
  `artifacts/online/context-integrity-failure-review.json`

Run from the repository root:

```powershell
python -m unittest discover -s tests -v
python -m acheon.evals.run --output artifacts/benchmark/latest.json
python scripts/generate_diagrams.py
python scripts/verify_openai_contribution.py
python scripts/verify_release.py
python scripts/build_release.py
python scripts/verify_release.py --require-archive
```

The optional paid online observation is reproduced separately with
`python scripts/run_openai_context_integrity_eval.py`; it reads an already approved
local credential and uses `store=false`. Public synthetic inputs remain in the
dataset; the script does not write model completion text, assembled grader payloads,
or provider request IDs.

Timing and the top-level report digest change across hosts because timing is part of
the report; selected IDs, absolute selection metrics, workload digest, and
configuration digest are deterministic for the fixed release input.

