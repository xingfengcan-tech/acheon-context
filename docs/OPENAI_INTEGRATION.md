# OpenAI integration

## Why the Responses API

OpenAI's current guidance distinguishes direct custom orchestration from SDK-managed
agent loops. Acheon owns selection, state, and branching, so the Responses API is
the narrowest fit. The local compiler remains useful with any runtime.

Official references:

- [GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/model-guidance?model=gpt-5.6-sol)
- [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)
- [Agents and Responses API comparison](https://developers.openai.com/api/docs/guides/agents)
- [Official Python library](https://github.com/openai/openai-python)

## Controlled request shape

- Model default: `gpt-5.6-sol`.
- Static developer instructions define the trust boundary.
- Dynamic context and the current query are user input.
- `store=False` avoids relying on stored provider conversation state.
- The adapter returns `response.model`, the Responses object ID, HTTP request ID when
  exposed by the SDK, usage, status details, observation time, and latency.
- The official client is bounded to a 60-second attempt timeout with at most one
  retry by default.
- The model cannot mutate local memory directly. A future extraction feature would
  create typed proposals that local validation must accept before storage.

## Native capability boundary

GPT-5.6 has its own context window, reasoning behavior, prompt caching, and provider
conversation features. Acheon does not replace or enlarge them. It decides which
application records to supply within a chosen budget and exposes that decision.

## Credential and evidence status

The repository never contains a key. Offline preview and evaluation work without
one. A securely authorized live call over public seeded demo data is recorded at
`artifacts/online/latest.json`; no credential or private payload is retained. That
single receipt demonstrates the runtime path, not comparative answer quality.
