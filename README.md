# DeepInfra API Integration Test

Quick connectivity and latency test for DeepInfra's OpenAI-compatible API endpoint.

## Models Tested

| Model | Purpose |
|---|---|
| `bytedance-seed/seed-2.0-mini` | Cheap, fast responses |
| `hermes-3-llama-3.1-405b` | Powerful reasoning |
| `Qwen/Qwen3-235B-A22B` | Synthesis tasks |

## Setup

The script looks for the API key in this order:

1. `DEEPINFRA_API_KEY` environment variable
2. `~/.openclaw/workspace/.env` or `~/.env` file
3. OpenClaw config (`~/.openclaw/openclaw.json`)

```bash
# Option 1: export directly
export DEEPINFRA_API_KEY=your_key_here

# Option 2: add to .env
echo "DEEPINFRA_API_KEY=your_key" >> ~/.openclaw/workspace/.env
```

## Run

```bash
python3 test.py
```

No external dependencies — uses only Python stdlib (`urllib`, `json`).

## Output

- Per-model latency and response preview
- Summary table with quality heuristic
- Full response text for each model
- Exit code 0 on success, 1 if any model fails
