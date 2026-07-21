# Evaluation methodology

## Question

Under the same estimated-unit context budget, does Acheon select more current, relevant records and
fewer forbidden records than simple history and lexical baselines on a disclosed,
fixed-seed long-history benchmark?

## Evidence levels

- **Contract:** exact unit or integration assertion.
- **Synthetic observation:** result on the repository's generated cases.
- **Live model observation:** paid physical GPT-5.6 calls recorded with returned
  model IDs and usage.
- **Independent evidence:** replication by another party on an unseen workload.

The initial automated package is expected to contain the first two levels. Missing
levels remain missing; they are not inferred from passing tests.

## Dataset

The generator creates six synthetic developer-workflow configurations across long
histories with fixed seeds. They share a disclosed role template and vary the
amount and recency of distractor evidence. Probes include:

- an early instruction that must survive later noise;
- a decision replaced by a newer decision;
- linked evidence required by a selected claim;
- similar distractors from the same namespace;
- out-of-scope records;
- explicit revocation and expiry;
- exact artifact references and similar lexical distractors.

Separate unit/integration contracts cover hostile instruction-like record text,
JSON data boundaries, namespace tampering, protected dependency bundles, and live
counterpart inclusion for disputed records. Those
contracts do not establish that a model will always resist prompt injection.

Each case declares gold relevant IDs, forbidden IDs, scope, query, and an
estimated-token-unit budget. All strategies use the same deterministic renderer and
provider-independent estimator; these units are not exact GPT tokenizer counts. The
generator and grader are public, so this is a transparent engineering benchmark, not
a hidden generalization test.

## Equal-budget baselines

1. **Chronological prefix:** oldest records first until the budget is full.
2. **Recent tail:** newest records first until the budget is full.
3. **Lexical top-k:** query-overlap ranking, with no lifecycle/link/lane logic.
4. **Acheon:** the full selector.

## Primary metrics

- Recall@budget over gold relevant IDs.
- Precision over selected IDs.
- Forbidden inclusion rate.
- Budget violation rate.

Secondary metrics include dependency completeness, deterministic digest agreement,
selected estimated-unit count, and compile latency. Absolute values are always reported.

## Statistics

The runner uses case-level paired differences and a fixed-seed bootstrap interval.
The report names the sample count, seed, configuration digest, workload digest,
Python/platform, failures, and a content digest. A positive point estimate whose 95%
interval includes zero is `inconclusive`, not verified improvement.

## Ablations

Lifecycle filtering, scope filtering, rank fusion, diversity, linked-record closure,
and type-lane reservation are disabled one at a time. Ablations diagnose this
implementation; they do not establish a biological, cognitive, or model-internal
mechanism.

## Online protocol

When secure API access is available, compare raw GPT-5.6 and Acheon with the same
model, current query, output contract, input budget, and repeated cases. Record the
returned model ID, request count, input/output tokens, latency, cost when available,
and every failure. Keep `store=False` and avoid `previous_response_id` so invisible
conversation state does not confound the comparison.

The checked-in `artifacts/online/latest.json` records one completed GPT-5.6 Sol
smoke test and provider receipt. It establishes runtime connectivity and receipt
capture only. The same-model comparison described above has not been run, so online
comparative effectiveness is **not evaluated**.
