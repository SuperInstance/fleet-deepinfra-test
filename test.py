#!/usr/bin/env python3
"""DeepInfra API integration test — connectivity, latency, and response quality."""

import os
import sys
import time
import json
import urllib.request
import urllib.error

API_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
TEST_PROMPT = (
    "In one paragraph, explain the conservation law γ + η = C "
    "as it applies to distributed agent systems."
)
MAX_TOKENS = 300

MODELS = [
    "bytedance-seed/seed-2.0-mini",
    "hermes-3-llama-3.1-405b",
    "Qwen/Qwen3-235B-A22B",
]


def get_api_key():
    """Find the DeepInfra API key from env, .env files, or OpenClaw config."""
    # 1. Environment variable
    key = os.environ.get("DEEPINFRA_API_KEY")
    if key:
        return key

    # 2. .env files
    for path in [
        os.path.expanduser("~/.openclaw/workspace/.env"),
        os.path.expanduser("~/.env"),
    ]:
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DEEPINFRA_API_KEY="):
                        return line.split("=", 1)[1].strip().strip("'\"")
        except FileNotFoundError:
            pass

    # 3. OpenClaw config
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        key = cfg.get("models", {}).get("providers", {}).get("deepinfra", {}).get("apiKey")
        if key:
            return key
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    return None


def call_model(api_key: str, model: str) -> dict:
    """Send a chat completion request and return result dict."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": TEST_PROMPT}],
        "max_tokens": MAX_TOKENS,
    }).encode()

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read())
        latency = time.perf_counter() - t0
        content = body["choices"][0]["message"]["content"].strip()
        usage = body.get("usage", {})
        return {
            "model": model,
            "status": "✅ OK",
            "latency_s": round(latency, 2),
            "tokens_prompt": usage.get("prompt_tokens", "?"),
            "tokens_completion": usage.get("completion_tokens", "?"),
            "response": content,
            "error": None,
        }
    except urllib.error.HTTPError as e:
        latency = time.perf_counter() - t0
        err_body = ""
        try:
            err_body = e.read().decode()[:200]
        except Exception:
            pass
        return {
            "model": model,
            "status": f"❌ HTTP {e.code}",
            "latency_s": round(latency, 2),
            "tokens_prompt": "?",
            "tokens_completion": "?",
            "response": "",
            "error": err_body or str(e),
        }
    except Exception as e:
        latency = time.perf_counter() - t0
        return {
            "model": model,
            "status": f"❌ {type(e).__name__}",
            "latency_s": round(latency, 2),
            "tokens_prompt": "?",
            "tokens_completion": "?",
            "response": "",
            "error": str(e),
        }


def quality_score(response: str) -> str:
    """Quick heuristic quality rating."""
    if not response:
        return "N/A"
    words = len(response.split())
    has_law = any(w in response.lower() for w in ["conservation", "distributed", "agent"])
    if words < 20:
        return "⚠️  Short"
    elif has_law and words > 40:
        return "⭐ Good"
    elif has_law:
        return "✅ Decent"
    else:
        return "🤔 Off-topic"


def main():
    print("=" * 70)
    print("DeepInfra API Integration Test")
    print("=" * 70)

    api_key = get_api_key()
    if not api_key:
        print("\n❌ No DEEPINFRA_API_KEY found. Set it via:")
        print("   export DEEPINFRA_API_KEY=your_key")
        print("   or add it to ~/.openclaw/workspace/.env")
        sys.exit(1)

    print(f"\n🔑 API key found ({api_key[:6]}...{api_key[-4:]})")
    print(f"📡 Endpoint: {API_URL}")
    print(f"📝 Prompt: {TEST_PROMPT[:80]}...")
    print(f"🤖 Models: {len(MODELS)}\n")

    results = []
    for model in MODELS:
        print(f"→ Testing {model} ...", flush=True)
        result = call_model(api_key, model)
        results.append(result)
        print(f"  {result['status']}  {result['latency_s']}s")
        if result["error"]:
            print(f"  Error: {result['error'][:120]}")
        else:
            preview = result["response"][:150].replace("\n", " ")
            print(f"  Response: {preview}...")
        print()

    # Summary table
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Model':<35} {'Status':<12} {'Latency':>8} {'Quality':<12} {'Tokens':>8}")
    print("-" * 70)
    for r in results:
        q = quality_score(r["response"])
        tokens = r["tokens_completion"]
        print(
            f"{r['model']:<35} {r['status']:<12} "
            f"{r['latency_s']:>6.2f}s  {q:<12} {str(tokens):>8}"
        )
    print("-" * 70)

    # Full responses
    print("\n" + "=" * 70)
    print("FULL RESPONSES")
    print("=" * 70)
    for r in results:
        print(f"\n--- {r['model']} ({r['latency_s']}s) ---")
        print(r["response"] or r["error"] or "(no response)")
        print()

    # Exit code
    failures = sum(1 for r in results if r["error"])
    if failures:
        print(f"⚠️  {failures}/{len(results)} models failed")
        sys.exit(1)
    else:
        print("✅ All models responded successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
