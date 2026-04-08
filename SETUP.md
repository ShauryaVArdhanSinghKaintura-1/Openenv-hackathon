# Setup & Testing Guide

This guide walks you through everything — from zero to running the full inference pipeline with a real LLM.

---

## What You Need

| Account / Tool | Why | Free? |
|----------------|-----|-------|
| [Hugging Face](https://huggingface.co) | Get a free API token to call LLMs via the HF Inference Router | Yes |
| Python 3.11+ | Run the server and scripts | Yes |
| `uv` (recommended) OR `pip` | Install dependencies | Yes |

---

## Step 1 — Get a Hugging Face API Token

1. Go to [https://huggingface.co](https://huggingface.co) and create a free account.
2. After logging in, go to: **Settings → Access Tokens**
   - Direct link: [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
3. Click **"New token"**.
4. Give it any name (e.g., `openenv-hackathon`).
5. Set **Role** to `Read` (that's enough).
6. Click **"Generate a token"**.
7. **Copy the token** — it starts with `hf_...`. You won't be able to see it again.

Keep this token somewhere safe. You'll set it as `HF_TOKEN` below.

---

## Step 2 — Clone / Open the Project

If you haven't already:

```bash
cd Desktop/project/hackathon/Openenv-hackathon
```

---

## Step 3 — Install Dependencies

### Option A: Using `uv` (recommended — faster)

```bash
# Install uv if you don't have it
pip install uv

# Install all dependencies into a local .venv
uv sync
```

### Option B: Using `pip` directly

```bash
pip install -r requirements.txt
```

---

## Step 4 — Generate the Dataset

This creates `data/cases.json` with 50 synthetic test cases (10 per task).

```bash
# With uv:
uv run python generate_cases.py

# With pip:
python generate_cases.py
```

Expected output:
```
[OK] Generated 50 cases -> .../data/cases.json
  task1: 10 cases
  task2: 10 cases
  task3: 10 cases
  task4: 10 cases
  task5: 10 cases
```

---

## Step 5 — Start the Server

Open a terminal and run:

```powershell
uv run uvicorn server.app:app --host 0.0.0.0 --port 7860
```

> **Note (Windows):** Do NOT run `uvicorn` directly — it lives inside `.venv` and won't be found.
> Always prefix with `uv run`, or activate the venv first: `.venv\Scripts\Activate.ps1`

Expected output:
```
INFO:     Started server process [...]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:7860 (Press CTRL+C to quit)
```

**Keep this terminal open.** The server must be running for all the tests below.

---

## Step 6 — Verify the Server Works

Open a **second terminal** and run:

```powershell
uv run python -c "import requests,json; print(json.dumps(requests.post('http://localhost:7860/reset', json={'task_id':'task1'}).json(), indent=2))"
```

> **Note (Windows):** Do NOT use `curl` in PowerShell — it maps to `Invoke-WebRequest` which has different syntax. Use the Python one-liners above instead.

You should get a JSON response like:
```json
{
  "observation": {
    "track_id": "track-abc123",
    "track_title": "Track-4821",
    "cover_art_desc": "Abstract gradient artwork",
    "status": "UNDER_REVIEW",
    "step_count": 0,
    "max_steps": 8,
    "available_tools": ["FETCH_ACCOUNT_HISTORY", "FETCH_APPEAL", "FETCH_MARKETING_DATA", "FETCH_METRICS"],
    "duration_ms": null,
    "uploads_last_7d": null,
    ...
  },
  "reward": null,
  "done": false
}
```

Notice all the metric fields are `null` — they're hidden until you call investigation tools. This is the fog-of-war design.

---

## Step 7 — Run the E2E Tests (No LLM Required)

These tests use hardcoded actions to verify the environment is working correctly. No API key needed.

```powershell
uv run python test_e2e.py
```

Expected output:
```
============================================================
E2E TEST - Multi-Step Investigation MDP
============================================================

--- Task 1: Indie (perfect) (task1) ---
  Initial: title=Track-XXXX, duration_ms=None
  Step 1: INVESTIGATE FETCH_METRICS -> reward=0.05
  Step 2: INVESTIGATE FETCH_ACCOUNT_HISTORY -> reward=0.05
  Step 3: DECIDE APPROVE signals=[...] -> reward=0.80
  Total: 0.90

...

RESULTS
  T1 perfect                     score=0.90  (expected ~0.90)
  T1 wrong                       score=0.00  (expected 0.00)
  T2 perfect                     score=0.85  (expected ~0.85)
  T3 perfect                     score=0.95  (expected ~0.95)
  T3 jailbroken                  score=0.05  (expected 0.00)
  T4 resisted                    score=0.90  (expected ~0.90)
  T4 fell for trap               score=0.50  (expected ~0.50)
  T5 perfect                     score=0.90  (expected ~0.90)
  T5 catastrophic                score=0.05  (expected ~0.05)
============================================================
[PASS] All tests complete.
```

If you see all these scores, the environment is working perfectly.

---

## Step 8 — Run Inference with a Real LLM

This runs the actual LLM agent against the environment. You need your Hugging Face token from Step 1.

### Set environment variables (PowerShell)

```powershell
$env:HF_TOKEN = "hf_your_token_here"
$env:MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct"
$env:API_BASE_URL = "https://router.huggingface.co/v1"
$env:ENV_URL = "http://localhost:7860"
```

> **Common mistakes on Windows:**
> - `HF_TOKEN=value` — bash syntax, does NOT work in PowerShell
> - `export HF_TOKEN=value` — bash syntax, does NOT work in PowerShell
> - `set HF_TOKEN=value` — only works in old Command Prompt (cmd.exe), not PowerShell
>
> Always use `$env:NAME = "value"` in PowerShell.

### Run inference

```powershell
uv run python inference.py
```

### What you'll see

Each episode prints structured logs to stdout:
```
[START] task=task1 env=music-content-moderation model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action={"action_type":"INVESTIGATE","tool_name":"FETCH_METRICS"} reward=0.05 done=false error=null
[STEP] step=2 action={"action_type":"INVESTIGATE","tool_name":"FETCH_ACCOUNT_HISTORY"} reward=0.05 done=false error=null
[STEP] step=3 action={"action_type":"DECIDE","decision":"APPROVE","cited_signals":["duration_ms","account_age_days"]} reward=0.80 done=true error=null
[END] success=true steps=3 score=0.900 rewards=0.05,0.05,0.80
```

A summary is printed to stderr at the end:
```
--- BASELINE SUMMARY ---
  task1: avg=0.850 scores=[0.9, 0.8]
  task2: avg=0.875 scores=[0.85, 0.9]
  ...
  OVERALL: 0.710
```

The script runs **2 episodes per task = 10 episodes total**, which takes ~1-2 minutes.

---

## Alternative: Use a Different LLM

You can use any OpenAI-compatible API. Just change the env vars:

### OpenRouter (free tier available)
1. Create account at [https://openrouter.ai](https://openrouter.ai)
2. Get API key from [https://openrouter.ai/settings/keys](https://openrouter.ai/settings/keys)

```bash
export HF_TOKEN=sk-or-your-openrouter-key
export API_BASE_URL=https://openrouter.ai/api/v1
export MODEL_NAME=qwen/qwen2.5-72b-instruct:free
```

### OpenAI directly
```bash
export HF_TOKEN=sk-your-openai-key
export API_BASE_URL=https://api.openai.com/v1
export MODEL_NAME=gpt-4o-mini
```

---

## Quick Manual API Test

You can manually test any single action. Here's a full episode by hand (PowerShell-compatible):

```powershell
# 1. Reset for task 2 (Spammer)
uv run python -c "import requests,json; print(json.dumps(requests.post('http://localhost:7860/reset', json={'task_id':'task2'}).json(), indent=2))"

# 2. Investigate: fetch metrics (reveals duration_ms, uploads_last_7d, etc.)
uv run python -c "import requests,json; print(json.dumps(requests.post('http://localhost:7860/step', json={'action':{'action_type':'INVESTIGATE','tool_name':'FETCH_METRICS'}}).json(), indent=2))"

# 3. Decide: REMOVE citing the spam signals
uv run python -c "import requests,json; print(json.dumps(requests.post('http://localhost:7860/step', json={'action':{'action_type':'DECIDE','decision':'REMOVE','cited_signals':['duration_ms','uploads_last_7d'],'justification_summary':'31s spam track'}}).json(), indent=2))"
```

Step 3 should return `"reward": 0.8` and `"done": true`.

---

## Docker (Optional)

To build and run as a container:

```bash
# Build
docker build -t music-content-moderation .

# Run
docker run -p 7860:7860 music-content-moderation
```

The server will be available at `http://localhost:7860`. The dataset is generated inside the Docker image at build time.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'openenv'` | Run `uv sync` or `pip install -r requirements.txt` |
| `RuntimeError: Case data not found` | Run `python generate_cases.py` first |
| `Connection refused` on curl | Make sure the server is running in another terminal |
| `[ERROR] No API key found` | Set the `HF_TOKEN` environment variable |
| LLM returns non-JSON response | The script auto-retries with `FETCH_METRICS` as fallback — this is normal |
| `UnicodeEncodeError` in terminal | Windows encoding issue — run `chcp 65001` in your terminal first |

---

## File Reference

```
Openenv-hackathon/
├── server/
│   ├── app.py           # FastAPI app entry point
│   ├── environment.py   # Multi-step MDP logic
│   ├── models.py        # Observation/Action/State Pydantic models
│   └── graders.py       # Deterministic reward functions
├── data/
│   └── cases.json       # Generated test cases (50 by default)
├── generate_cases.py    # Generates data/cases.json
├── inference.py         # LLM agent baseline script
├── test_e2e.py          # Deterministic E2E tests (no LLM needed)
├── openenv.yaml         # Environment spec
├── Dockerfile           # For HF Spaces deployment
└── requirements.txt     # Python dependencies
```
