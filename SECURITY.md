# Security and data handling

## Trust boundary

Memory text is untrusted data. Acheon never treats commands inside a stored record
as application code. The GPT adapter keeps a static developer policy separate from
the dynamic context packet and labels the packet as reference data.

## Local storage

- SQLite is local by default.
- Namespace selection is explicit.
- Revisions preserve history for audit; normal retrieval exposes only the current
  revision.
- Revoked, expired, and superseded records are excluded before ranking.
- The audit log stores record checksums and lifecycle metadata, not raw record text.

SQLite files may still contain private record content. Do not commit `data/`, copy a
database into screenshots, or publish a database as sample data without review.

## Model transmission

The offline path transmits nothing. The optional GPT-5.6 path sends the compiled
packet and current query to OpenAI. Review selected IDs and the packet preview before
using sensitive data. The controlled adapter uses `store=False`; provider retention
and account policies remain governed by the OpenAI service and project settings.

The HTTP demo binds to loopback and forces preview mode by default, even when an API
key exists. Non-loopback binding requires `ACHEON_HTTP_TOKEN`; enabling paid model
calls over HTTP additionally requires the explicit `--enable-live-http` flag and a
token of at least 16 characters. The sample server is still not a multi-tenant auth
service and should not be exposed as a public production API.

## Prompt injection

Stored content can contain hostile instructions. Acheon applies three controls:

1. dynamic memory is rendered as structured user data;
2. only typed instruction records can represent prior user-level constraints, and
   only when compatible with the current request and developer policy;
3. the static runtime policy rejects role upgrades, tool commands, credential
   requests, and side-effect authorization found in record text.

This reduces risk; it is not a complete prompt-injection defense. Do not grant the
model high-impact tools solely because a packet was compiled by Acheon.

## Integrity

Every mutation and compile creates a hash-chained audit event. `verify_audit()`
checks the event chain and the current persisted record bytes; record reads reject
checksum mismatches. Before every write transaction mutates state, it verifies the
existing chain and state so a detected partial tamper cannot be re-anchored by an
otherwise valid later operation. The release verifier separately checks the publishable source
tree and benchmark receipt—it does not validate an arbitrary database. A local hash
chain is not a signature, remote attestation, or third-party audit.

Without an externally stored head or signature, a sufficiently privileged attacker
can truncate a valid tail or rewrite the database and recompute local hashes. Use an
external append-only anchor when adversarial database administrators are in scope.

## Credentials

- Never commit `.env`, API keys, paid-call payloads, or decrypted secrets.
- `.env.example` contains names only.
- Runtime errors must not print an API key.
- Rotate a credential immediately if it appears in terminal output, a task, an
  artifact, or version control.

## Reporting a vulnerability

Before a public repository exists, report privately to the project owner. Do not
include private data or live credentials in a report.
