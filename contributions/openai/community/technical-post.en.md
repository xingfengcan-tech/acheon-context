# A reproducible control plane for long-horizon context integrity

I am releasing Acheon, an open-source alpha for deterministic and auditable context
governance in long-running AI workflows:

https://github.com/xingfengcan-tech/acheon-context

Long-running agents can fail even when relevant information exists in their
history. An old constraint may disappear under newer noise, a revoked decision may
return, records from another project may leak into the task, or a selected claim may
lose the evidence it depends on. Semantic similarity alone does not express these
governance rules.

## What Acheon explores

Acheon sits between a record store or retriever and the model. It provides:

- typed, versioned records with provenance, trust, scope, and lifecycle;
- hard exclusion of expired, revoked, superseded, and out-of-scope records before
  ranking;
- protected constraints, dependency-complete selection, and explicit conflict
  visibility under a fixed estimated-token budget;
- deterministic selected/omitted reason codes for every current record;
- canonical context packet digests and a tamper-evident local audit receipt;
- an offline CLI and web demo plus an optional GPT-5.6 Sol Responses API adapter.

The core is model-independent and runs without network access. It does not change
model weights, expand a provider context window, or create permanent model memory.

## Reproducible evidence and its boundary

The release includes 61 unit and integration tests and a disclosed 240-case
synthetic selection workload. Under the same 640-unit rendered-packet budget,
Acheon records 1.000 recall, 0.857 precision, zero forbidden-record cases, zero
budget violations, and deterministic outputs. The three controls are chronological
prefix, recent tail, and lexical top-k. All failures and six ablations are included.

These are engineering-contract results, not a claim that GPT-5.6 became more
intelligent. The generator shares a common role structure, the controls are simple,
and the rank-fusion ablation has no measured effect on this workload. The release
also contains one successful GPT-5.6 Sol runtime receipt, but no raw-versus-Acheon
answer-quality comparison.

## What I would value feedback on

The repository now includes a proposed 24-sample OpenAI Evals contribution for
early-constraint retention, supersession, revocation, dependency completeness,
scope isolation, conflict disclosure, untrusted-history handling, budget priority,
and calibrated uncertainty. It also includes 16 provisionally labeled positive and
negative answers for meta-evaluating the grader. One preliminary GPT-5.6 Sol run
produced 16/16 agreement with those provisional labels and 23/24 automated primary
passes; a targeted reproduction check of the one failure omitted two required
traceability details. Independent human review of the samples, reference answers,
and labels remains a pre-submission gate. This is not an Acheon-versus-baseline
result. The next evidence gate is a same-model, equal-token comparison against
stronger hybrid retrieval, summarization, and long-context baselines on held-out
tasks.

I would especially appreciate feedback on:

1. which governance failures are missing from the proposed eval;
2. which strong, reproducible baselines should be mandatory;
3. how to separate context-selection quality from downstream model compliance;
4. what packet-level interoperability contract would make this useful across
   agent frameworks.

Release and methodology:

- Repository: https://github.com/xingfengcan-tech/acheon-context
- Release: https://github.com/xingfengcan-tech/acheon-context/releases/tag/v0.1.0
- Evaluation: https://github.com/xingfengcan-tech/acheon-context/blob/main/docs/EVALUATION.md
- Proposed OpenAI Evals contribution: https://github.com/xingfengcan-tech/acheon-context/tree/main/contributions/openai/evals
- Limitations: https://github.com/xingfengcan-tech/acheon-context/blob/main/docs/LIMITATIONS.md
