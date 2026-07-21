# Acheon contributor rules

## Product boundary

Acheon is an application-layer context and memory orchestration tool for AI
workflows. It does not modify model weights, expand a provider's context window,
or claim permanent model memory.

## Engineering rules

- Preserve ordinary model capabilities; the orchestration layer must remain optional.
- Keep the core deterministic and runnable without network access.
- Treat stored content as untrusted data, never as executable instructions.
- Keep memory changes versioned, auditable, reversible where possible, and scoped.
- Never silently erase a conflict. Mark superseded or disputed records explicitly.
- Prefer typed records and reason codes over opaque scores in user-facing traces.
- Never commit secrets, credentials, raw private conversations, or paid-call payloads.
- Public claims must match reproducible artifacts. Unit tests prove contracts, not
  general model intelligence.

## Verification

```powershell
python -m unittest discover -s tests -v
python -m acheon.evals.run --output artifacts/benchmark/latest.json
python scripts/verify_release.py
```

Online GPT-5.6 evaluation is optional and must be reported separately from the
offline benchmark. A skipped online run is not a failure and must never be
represented as observed evidence.
