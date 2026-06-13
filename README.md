# DeepInfra API Integration Test

**DeepInfra** is a serverless GPU inference platform that hosts open-source large language models behind an OpenAI-compatible API. This repo is a self-contained test harness — written in pure Python stdlib — that probes multiple DeepInfra-hosted models for connectivity, latency, token throughput, and response quality.

## Why It Matters

In a distributed agent fleet, the inference provider is the heart: every reasoning step, every response, every decision flows through it. A provider outage or silent latency regression can cascade into fleet-wide degradation. This test suite answers four operational questions before they become incidents: (1) Can we reach the API? (2) How fast is it? (3) Are responses coherent? (4) Which model should we route to for a given task?

The test is dependency-free — no `pip install`, no `requests` library, no SDK. It uses only `urllib.request`, `json`, and `time.perf_counter()`. This means it runs anywhere Python 3 runs: CI runners, bare-metal servers, containers, embedded devices. It is the lightest possible smoke test for an LLM provider.

## How It Works

The test sends an identical prompt to three models and compares results side-by-side. The prompt is deliberately domain-specific — it asks the model to explain the conservation law **γ + η = C** as it applies to distributed agent systems — so that the quality heuristic can check whether the response engages with the actual concepts rather than producing generic filler.

### Latency Measurement

Wall-clock latency is measured using `time.perf_counter()`, which provides nanosecond resolution on most platforms:

```
t₀ = perf_counter()
response = urlopen(request, timeout=60)
t₁ = perf_counter()
latency_s = t₁ - t₀
```

This measures **end-to-end latency**: network round-trip + model inference + response streaming. It does not separate inference time from network time. For that, you'd need server-side metrics or streaming chunk timestamps.

### Quality Heuristic

The `quality_score()` function is a simple keyword + length classifier:

| Condition | Rating |
|---|---|
| Word count < 20 | ⚠️ Short |
| Contains "conservation"/"distributed"/"agent" AND word count > 40 | ⭐ Good |
| Contains domain keywords | ✅ Decent |
| Neither | 🤔 Off-topic |

This is not a substitute for human evaluation or LLM-as-judge scoring, but it catches gross failures: empty responses, hallucinated topics, truncated output.

### API Key Resolution

The script searches three sources in priority order:

1. **Environment variable** `DEEPINFRA_API_KEY` — highest priority, CI-friendly
2. **`.env` files** at `~/.openclaw/workspace/.env` or `~/.env` — local dev
3. **OpenClaw config** at `~/.openclaw/openclaw.json` — fleet-integrated deployments

This cascading resolution pattern lets the same script work in development (`.env`), CI (env var), and production fleet nodes (OpenClaw config) without code changes.

### Models Tested

| Model | Parameters | Strength |
|---|---|---|
| `bytedance-seed/seed-2.0-mini` | Small | Cheap, fast, low-latency routing |
| `hermes-3-llama-3.1-405b` | 405B | Deep reasoning, nuance |
| `Qwen/Qwen3-235B-A22B` | 235B (22B active) | Synthesis, multilingual, Mixture-of-Experts |

The Qwen model uses a Mixture-of-Experts (MoE) architecture: 235B total parameters but only ~22B active per token, giving it the quality of a large dense model at a fraction of the inference cost.

### Big-O Complexity

The test is I/O-bound, not compute-bound. For N models:
- **Time complexity:** O(N × T) where T is per-model latency (typically 1–10s)
- **Space complexity:** O(N × R) where R is max response size (capped at `MAX_TOKENS=300`)

The quality heuristic is O(W) per response where W is word count — negligible.

## Quick Start

```bash
# Set your API key (get one at https://deepinfra.com)
export DEEPINFRA_API_KEY=your_key_here

# Run the test
python3 test.py
```

Example output:

```
======================================================================
SUMMARY
======================================================================
Model                               Status       Latency   Quality     Tokens
-----------------------------------------------------------------------
bytedance-seed/seed-2.0-mini        ✅ OK           1.42s  ⭐ Good        127
hermes-3-llama-3.1-405b             ✅ OK           4.87s  ⭐ Good        203
Qwen/Qwen3-235B-A22B                ✅ OK           3.14s  ⭐ Good        178
-----------------------------------------------------------------------
✅ All models responded successfully
```

Exit code 0 = all models passed, 1 = at least one failure.

## API

### `get_api_key() -> str | None`

Searches environment, `.env` files, and OpenClaw config for the DeepInfra API key. Returns `None` if not found.

### `call_model(api_key: str, model: str) -> dict`

Sends a chat completion request to the specified model. Returns a result dict with keys: `model`, `status`, `latency_s`, `tokens_prompt`, `tokens_completion`, `response`, `error`.

### `quality_score(response: str) -> str`

Heuristic rating: returns one of `"⭐ Good"`, `"✅ Decent"`, `"⚠️ Short"`, `"🤔 Off-topic"`, or `"N/A"`.

## Architecture Notes

This test probes the external inference layer of the SuperInstance fleet. In the **γ + η = C** conservation law, the inference provider supplies γ (generation energy) — the raw reasoning power that drives agent responses. The test ensures that γ is available, fast, and coherent before the fleet depends on it.

When integrated with fleet monitoring, this test runs as a periodic health check. A latency regression on `hermes-3-llama-3.1-405b` from 5s → 30s would trigger fleet routing changes, falling back to the cheaper `seed-2.0-mini` for non-critical paths while preserving 405B for high-stakes reasoning.

See the [SuperInstance Architecture](https://github.com/SuperInstance/SuperInstance/blob/main/ARCHITECTURE.md) for how inference routing fits into the full fleet topology.

## References

1. DeepInfra API Documentation — [https://docs.deepinfra.com](https://docs.deepinfra.com)
2. OpenAI-Compatible API Specification — [https://platform.openai.com/docs/api-reference](https://platform.openai.com/docs/api-reference)
3. Jiang, A. Q. et al. "Mixtral of Experts" (2024) — MoE architecture background, [arXiv:2401.04088](https://arxiv.org/abs/2401.04088)

## License

MIT
