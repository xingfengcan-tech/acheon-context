# OpenAI contribution publication boundary

This directory contains the reviewed public contribution package for Acheon. It
describes observable behavior, reproducible evidence, and integration boundaries.
It is not a disclosure of private research notes or unpublished design derivations.

## Approved public material

- the application-layer product boundary;
- typed records, lifecycle states, scope isolation, dependencies, conflicts, and
  version history as implemented in the public repository;
- deterministic selection and omission reason codes;
- canonical context packets, checksums, and tamper-evident local audit receipts;
- source code already present in the reviewed public release;
- synthetic benchmark inputs, methodology, full results, failures, and limitations;
- sanitized model-behavior eval prompts, reference answers, and grading rubrics;
- the single live runtime receipt with no answer text or private payload;
- the 24-sample context-integrity aggregate receipt and narrow human-review receipt,
  neither of which retains raw model output;
- setup instructions, diagrams, screenshots, and public release links.

## Material that must remain private

- unpublished prototype theories, original derivations, and internal research notes;
- hidden prompts, private threshold rationales, and unpublished experimental logs;
- raw personal or commercial conversations and customer data;
- credentials, environment files, API keys, authorization headers, or paid-call
  payloads;
- development Git history or refs outside the reviewed public archive;
- provider metadata beyond fields already intentionally published in the release;
- any claim that cannot be reproduced from the public artifacts.

## Claim boundary

Approved claim:

> Acheon is an alpha application-layer context governance compiler. It makes
> selection, lifecycle, scope, dependency, conflict, and budget decisions
> deterministic and inspectable, and it has credible high-impact potential for
> long-running AI workflows.

Claims that are not approved:

- Acheon changes model weights or a provider's native context window;
- Acheon gives a model permanent memory;
- the checked-in offline benchmark proves general answer-quality improvement;
- one live smoke test proves a universal or paradigm-level gain;
- one standalone 24-sample run proves Acheon improves model answers;
- OpenAI reviewed, endorsed, certified, or partnered on the project;
- the implementation is the first or only system to address long-term memory.

## Submission controls

Only the files listed by `disclosure-manifest.json` may be copied into a third-party
submission. Identity fields, rights attestations, data-sharing choices, legal
agreements, and final external submission remain operator decisions. An automated
process may prepare and validate those fields, but must not invent or accept them.
