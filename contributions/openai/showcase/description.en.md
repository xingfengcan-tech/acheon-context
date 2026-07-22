# Acheon Showcase copy

## Title

Acheon: Auditable Context for Long-Running AI Workflows

## Tagline

A deterministic control layer that turns noisy histories into bounded,
inspectable context while preserving current constraints, dependencies, and
unresolved conflicts.

## Description

Acheon is an open-source application-layer context governance compiler for
long-running AI workflows. It stores typed, versioned records; excludes revoked,
expired, superseded, and out-of-scope material; preserves required dependencies and
visible conflicts; and emits a bounded canonical context packet with a reason code
for every selection decision.

The offline core includes a local UI, equal-budget controls, ablations, full
failures, a reproducible 240-case synthetic selection benchmark, and a separate
24-case model-behavior eval. An optional Responses API adapter sends the compiled
packet to GPT-5.6 Sol with stored history treated as untrusted data. Acheon does not
modify model weights, expand a provider context window, or claim permanent model
memory. Current evidence establishes engineering contracts and high-impact
potential, not an Acheon-attributable answer-quality improvement.

## Evidence note for reviewers

The checked-in benchmark measures record-selection contracts on a disclosed
synthetic generator. The one live API-path receipt proves the adapter completed. A
separate, single-run GPT-5.6 Sol context-integrity observation recorded 23/24
automated passes with a same-model grader and one targeted reproduction of a
traceability omission. The provisional labels and reference answers were primarily
drafted and checked by Codex/model agents; item-level independent human review is
pending. Neither is a raw-versus-Acheon comparison. The project publishes these
limitations so reviewers can reproduce exactly what is and is not established.
