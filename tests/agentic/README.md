# Agentic testing

Provider-agnostic agentic UI testing for MeshChatX. Two layers:

1. **Deterministic harnesses** (`.cjs` scripts) that always run: route
   coverage drift, heap profiling per interaction, i18n overflow scan,
   hostile input sweep, Electron update-apply flow. Zero LLM cost.
2. **Agent legs** that bolt an LLM on top for the parts a script cannot
   judge: generating context-matched hostile payloads, vision-judging
   locale screenshots, and freeform exploratory crawls driven through
   Playwright MCP by OpenCode.

## Provider setup

Everything speaks OpenAI-compatible `/chat/completions`, so any of these
work:

| Backend | Env |
| --- | --- |
| Ollama (default) | `AGENTIC_LLM_BASE_URL=http://127.0.0.1:11434/v1` `AGENTIC_LLM_MODEL=qwen2.5vl:7b` |
| LM Studio / llama.cpp | `AGENTIC_LLM_BASE_URL=http://127.0.0.1:1234/v1` + model id |
| OpenCode Console | `AGENTIC_LLM_BASE_URL=<console-endpoint>` `AGENTIC_LLM_API_KEY=oc_sk_...` |
| Any OpenAI-compatible | same three vars |

`AGENTIC_VISION_MODEL` overrides the model for screenshot judging when it
differs from the text model. Local endpoints need no API key.

**Never commit API keys.** Export them in your shell or CI secrets only.

## Deterministic legs

Run individually or via `run.sh`:

```sh
node tests/agentic/route-drift.cjs          # routes in router vs crawled specs
node tests/agentic/heap-profiler.cjs --json out/heap.json
node tests/agentic/i18n-sweep.cjs           # DOM overflow only
node tests/agentic/adversarial.cjs          # static hostile payloads
node tests/agentic/electron-update-flow.cjs # needs built app + xvfb
```

`route-drift.cjs` is the one leg wired unconditionally into CI: it is
pure file parsing and fails when a router path is not crawled or a crawled
path no longer exists.

## Agent legs (OpenCode)

`tests/agentic/opencode.jsonc` wires a `crawler` agent (edit/shell denied),
the Playwright MCP server, and slash commands for each task. Run from the
repo root:

```sh
cd tests/agentic
opencode run /agentic-crawl
opencode run /agentic-adversarial
opencode run /agentic-update-flow
opencode run /agentic-i18n
opencode run /agentic-heap
```

With a Console key: `export OPENCODE_API_KEY=oc_sk_...` and pick a
`opencode/*` model in `/models` or `model` in the config. With a local
model: `export AGENTIC_LLM_BASE_URL=http://127.0.0.1:11434/v1` and the
`agentic-local/default` model is picked up automatically.

The LLM-assisted scripts can also run without OpenCode:

```sh
node tests/agentic/i18n-sweep.cjs --judge   # vision verdicts per locale
node tests/agentic/adversarial.cjs --llm    # model-generated payloads
node tests/agentic/vision-judge.cjs a.png b.png "intent"  # pairwise diff verdict
```

## Safety rules the suite enforces

- Agents get Playwright tools, never shell or file write. The `crawler`
  agent config denies both.
- The deterministic crawlers use the same destructive-word blocklist as
  the e2e crawler, so agents cannot delete data or send messages.
- Vision judging reports `regression`/`intended`/`noise`/`flake` — it
  never writes baselines or marks failures green.
- The Electron update test crafts its own marker + payload; it never
  touches a real release or downloads anything.

## Reports

`tests/agentic/out/` — gitignored. JSON + screenshots land here.
