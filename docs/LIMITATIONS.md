# Limitations

- The token estimator is deterministic and provider-independent; its units are not
  exact GPT tokenizer counts or a guaranteed upper bound for every tokenizer/text.
- Lexical and metadata ranks do not provide full semantic retrieval.
- User-supplied types, scopes, links, and lifecycle states can be wrong.
- `ContextCompiler.compile(as_of=...)` applies lifecycle timing to the revisions
  that are current when compilation starts; it is not a historical snapshot or
  revision-time-travel API.
- A local hash chain detects covered tampering but is not cryptographic identity or
  third-party attestation. Without an external anchor it cannot prove that a valid
  audit tail was not truncated or recomputed by a privileged attacker.
- Prompt-injection controls reduce exposure but do not make untrusted content safe
  for high-impact tool use.
- Synthetic cases reflect their generator and developer-workflow assumptions.
- Offline selection metrics do not establish downstream GPT-5.6 answer quality.
- A model output can still ignore, misread, or hallucinate despite better-selected
  context.
- The first release is single-node and has no hosted auth, tenant service, vector
  index, or multi-user permission system.
- This project does not change model weights, context-window size, knowledge cutoff,
  reasoning process, or provider persistence guarantees.
