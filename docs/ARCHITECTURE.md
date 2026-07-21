# Architecture

## Design target

Acheon improves the **effective use** of an available context budget at the
application layer. It is intentionally independent of model weights and provider
conversation state.

## Flow

1. **Record** — A typed item carries a namespace, kind, topic, scope, source,
   lifecycle, trust class, optional links, and content checksum.
2. **Store** — SQLite keeps all revisions. A current-revision index supports normal
   reads; transitions append a new revision.
3. **Gate** — Inactive lifecycle states, expired records, and out-of-scope records
   are rejected before ranking.
4. **Candidate ranks** — Standard lexical overlap, exact references, type priority,
   and recency produce independent deterministic rankings.
5. **Fusion** — Reciprocal-rank-style fusion combines the ranks. No learned score or
   hidden model call is required.
6. **Budget plan** — Pinned constraints enter first. Type lanes preserve room for
   active continuity and evidence. Required links are closed before a parent record
   can enter. Standard maximal-marginal-relevance diversity reduces duplicates.
7. **Compile** — Records become a canonical JSON data envelope ordered into
   operating constraints, active continuity, relevant knowledge, and recent context.
   A final render-time check enforces the hard provider-independent estimate. This
   is not an exact GPT tokenizer count.
8. **Trace** — Every current record receives selected/omitted reason codes. The
   packet has a stable digest; the store appends a hash-chained activity receipt.
9. **Run** — Offline preview is the default. The optional Responses API adapter sends
   the packet as user data to GPT-5.6.

## Lifecycle semantics

- `active`: retrievable.
- `disputed`: retrievable with explicit conflict metadata.
- `superseded`: retained in history, excluded from retrieval.
- `revoked`: retained for audit, excluded from retrieval.
- `expired`: excluded from retrieval.

Adding a record that explicitly supersedes another record changes both current
states atomically. Revisions use optimistic checks when a caller supplies an expected
revision.

## Determinism boundary

Given the same current records, query, scope, time, budget, and configuration, the
selector and context digest are deterministic. Audit heads are intentionally not
stable because each activity is time-stamped. Model outputs are not claimed to be
deterministic.

## Failure behavior

- Missing linked requirements reject an optional parent; if the parent is protected,
  compilation fails explicitly.
- A write with a stale revision fails.
- Cross-namespace supersession fails.
- Render-time budget overflow removes only dependency-safe optional items. If the
  protected bundle itself cannot fit, compilation fails explicitly instead of
  silently dropping a protected record or breaking a dependency.
- An oversized empty envelope fails before an audit receipt is written.
- Selected and omitted reason codes describe mutually exclusive final states.
- A write refuses to proceed if the pre-existing local audit/state check fails.
- A missing API key returns an offline preview; it never fabricates a model answer.

## Non-goals

- training or fine-tuning a foundation model;
- expanding a provider's context window;
- vector-database replacement;
- autonomous external side effects;
- proving general intelligence or universal improvement.
