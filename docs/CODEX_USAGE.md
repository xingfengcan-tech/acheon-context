# How Codex was used

Codex was the primary engineering collaborator for the public implementation:

- translated the product goal into an evidence-bounded public architecture;
- checked current OpenAI Build Week, GPT-5.6, Responses API, and evaluation guidance;
- designed the clean public architecture and confidentiality boundary;
- implemented storage, selection, compilation, audit, runtime, CLI, and demo paths;
- generated adversarial tests, equal-budget baselines, ablations, and release checks;
- ran the repository test and benchmark commands, inspected failures, and iterated;
- prepared the English submission description and under-three-minute demo script.

Concrete collaboration points included:

1. **Evidence boundary:** Codex separated deterministic selection-contract metrics
   from downstream model quality, retained failures and ablations, and prevented a
   successful live smoke test from being presented as a general improvement claim.
2. **Adversarial iteration:** Codex reproduced and fixed invalid supersession,
   untrusted pinned instructions, duplicate identifiers, threaded compilation
   snapshots, and conflict-counterpart starvation; each failure became a regression
   test rather than an undocumented prompt rule.
3. **Release safety:** Codex built an allowlisted, deterministic archive, secret and
   metadata checks, a tamper-evident audit verifier, an installable wheel path, and
   a narrated submission demo tied to public machine-readable evidence.

Key human decisions were to keep Acheon optional and application-layer, prefer
explicit lifecycle and reason codes over opaque memory claims, and publish narrow
reproducible evidence instead of claiming changes to GPT-5.6 itself.

The final Devpost form requires the `/feedback` session ID for the task containing
most core development. That ID is an operator-supplied release field and is not
invented by this repository.

Codex produced code and analysis; the submitter remains responsible for authorship
review, legal eligibility, private-information review, publication, and final claims.
