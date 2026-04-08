# UPDATE.md — Hackathon Submission Fix PRD

**Project:** Music Content Moderation — OpenEnv Hackathon  
**Repo:** `ShauryaVArdhanSinghKaintura-1/Openenv-hackathon`  
**Deadline:** April 8, 2026 11:59 PM IST  
**Purpose:** This document is a complete, actionable list of changes that Claude Code must apply to make the project submission-ready. Every item includes the exact file, the problem, and the fix.

---

## PRIORITY LEGEND

- 🔴 **CRITICAL** — Will cause disqualification if not fixed
- 🟡 **HIGH** — Will significantly hurt scoring or cause runtime failures
- 🟢 **MEDIUM** — Code quality / cleanup that improves judging impression

---

## 🔴 CRITICAL FIX 1: `.gitignore` is completely empty

**File:** `.gitignore`  
**Problem:** The `.gitignore` file is 0 bytes. `__pycache__/`, `.egg-info/`, `.claude/`, and compiled `.pyc` files are all tracked in the repo. This is unprofessional and can cause build conflicts.

**Fix:** Replace `.gitignore` contents with:

```
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.env
.claude/
*.egg
.venv/
venv/
```

---

## 🔴 CRITICAL FIX 2: Remove tracked junk files from git history

**Problem:** The following paths are committed to git and must be removed from tracking (but kept in `.gitignore`):

- `server/__pycache__/` (7 compiled .pyc files)
- `music_content_moderation.egg-info/` (6 files)
- `.claude/settings.local.json` (contains developer's Windows file paths — a security/privacy concern)

**Fix:** Run these git commands:

```bash
git rm -r --cached server/__pycache__/
git rm -r --cached music_content_moderation.egg-info/
git rm -r --cached .claude/
git commit -m "chore: remove tracked cache/build artifacts and .claude settings"
```

---

## 🔴 CRITICAL FIX 3: `num_cases` mismatch between `openenv.yaml` and `generate_cases.py`

**Files:** `openenv.yaml` and `generate_cases.py`  
**Problem:** `openenv.yaml` declares `num_cases: 60` for every task, but `generate_cases.py` has `NUM_PER_PROFILE = 10`, producing only 50 total cases (10 per task). The Dockerfile runs `python generate_cases.py` at build time, so the deployed image will have 50 cases, not 300. If the validator checks `num_cases` against actual data, this fails.

**Fix — Option A (RECOMMENDED for safety — keeps runtime under 20 min):**  
Update `openenv.yaml` — change every `num_cases: 60` to `num_cases: 10`:

```yaml
# In each of the 5 task entries:
    num_cases: 10
```

**Fix — Option B (more impressive for judging, but check runtime):**  
Update `generate_cases.py` line 17:

```python
NUM_PER_PROFILE = 60  # Was 10
```

And keep `openenv.yaml` as-is. But then update `inference.py` `episodes_per_task` to 1 (not 2) to stay under 20 min runtime. With 60 cases per task, the inference at `time.sleep(8)` per step would be: 5 tasks × 1 episode × ~5 steps × 8s = ~200s for sleeps + API time. This should fit.

**Decision:** Go with **Option A** unless you are confident about runtime. Consistency is more important than case count.

---

## 🔴 CRITICAL FIX 4: Step rewards can be negative — violates 0.0–1.0 constraint

**File:** `server/environment.py`  
**Problem:** In the `step()` method, an invalid tool call returns `reward = -0.05`. The hackathon requires "verify scores/reward in 0.0–1.0 range." A negative reward risks failing automated validation.

**Fix:** In `server/environment.py`, in the `step()` method under the `INVESTIGATE` branch, clamp the reward to be >= 0.0:

Change line 181 (the invalid tool penalty):
```python
# BEFORE:
reward = -0.05

# AFTER:
reward = 0.0  # Invalid tool — no reward, but no negative penalty
```

Alternatively, clamp all rewards before returning. At every point where `obs.reward = reward` is set, ensure:
```python
obs.reward = max(0.0, min(1.0, reward))
```

The safest approach: add a clamp right before every `return obs` in the `step()` method:
```python
obs.reward = max(0.0, min(1.0, reward))
```

Apply this to ALL return paths in `step()` (there are 6 return statements).

---

## 🔴 CRITICAL FIX 5: `.dockerignore` is missing `.claude/` entry

**File:** `.dockerignore`  
**Problem:** The `.claude/` directory (with developer-specific settings) will be copied into the Docker image. Not harmful but sloppy.

**Fix:** Add `.claude/` to `.dockerignore`:

```
__pycache__
*.pyc
*.pyo
.git
.env
*.egg-info
dist
build
uv.lock
test_e2e.py
test_standalone.py
.gemini
.claude
GUIDE.md
SETUP.md
```

Also add `test_standalone.py`, `GUIDE.md`, `SETUP.md` since they're not needed in the deployed image.

---

## 🔴 CRITICAL FIX 6: HF Space must be deployed and live

**Problem:** The hackathon requires a live Hugging Face Space tagged with `openenv` that returns HTTP 200 on `POST /reset`. Without this, the submission is automatically disqualified.

**Fix (manual steps — Claude Code cannot do this, the developer must):**

1. Create a Hugging Face Space (Docker type) at `https://huggingface.co/spaces`
2. Push the repo to the HF Space (or link the GitHub repo)
3. Ensure the Space is tagged with `openenv`
4. After deployment, verify:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" -X POST \
     -H "Content-Type: application/json" -d '{}' \
     https://<YOUR-SPACE>.hf.space/reset
   ```
   Must return `200`.
5. Also test: `GET /health`, `GET /state`, `POST /step`
6. Update the `README.md` with the HF Space URL

---

## 🟡 HIGH FIX 7: `ModerationState` is missing `step_count` field

**File:** `server/models.py`  
**Problem:** The `state` property in `environment.py` passes `step_count=_step_count` to `ModerationState(...)`, but the `ModerationState` class does NOT define a `step_count` field. Depending on Pydantic/OpenEnv BaseState configuration, this could:
- Be silently ignored (the `/state` endpoint returns incomplete data)
- Raise a ValidationError (crashing the `/state` endpoint)

**Fix:** Add `step_count` field to `ModerationState` in `server/models.py`:

```python
class ModerationState(BaseState):
    """Internal environment state exposed via /state endpoint."""
    step_count: int = Field(default=0, description="Current step in the episode")
    current_case_index: int = Field(default=0, description="Index of current case in shuffled list")
    total_cases: int = Field(default=0, description="Total cases loaded")
    episode_reward: float = Field(default=0.0, description="Accumulated reward for current episode")
    done: bool = Field(default=False, description="Whether episode is complete")
    revealed_keys: List[str] = Field(default_factory=list, description="Keys revealed via tools so far")
    tools_called: List[str] = Field(default_factory=list, description="Tools called so far")
```

---

## 🟡 HIGH FIX 8: `inference.py` has hardcoded `time.sleep(8)` causing slow runtime

**File:** `inference.py`, line 215  
**Problem:** `time.sleep(8)` between every investigation step. With 5 tasks × 2 episodes × ~4 investigation steps = ~40 sleeps × 8s = 320 seconds just in sleeps. Plus API latency. Total runtime approaches 10+ minutes, dangerously close to the 20-minute limit.

**Fix:** Reduce sleep or make it conditional:

```python
# BEFORE:
time.sleep(8)  # stay under 8 req/min free tier limit

# AFTER:
time.sleep(1)  # Small delay between steps; HF router handles rate limits
```

The `https://router.huggingface.co/v1` endpoint is the default and doesn't have the same aggressive rate limits as free-tier OpenRouter. A 1-second delay is sufficient. The retry logic already handles 429s with exponential backoff.

---

## 🟡 HIGH FIX 9: Version mismatch between `pyproject.toml` and `openenv.yaml`

**Files:** `pyproject.toml` (says `version = "1.0.0"`) and `openenv.yaml` (says `version: "2.0.0"`)  
**Problem:** Inconsistent versioning looks careless and could confuse validators.

**Fix:** Update `pyproject.toml` line 3:
```toml
version = "2.0.0"
```

---

## 🟡 HIGH FIX 10: `ground_truth` field is stored inside observation data

**File:** `generate_cases.py`  
**Problem:** Every case has `"ground_truth": "APPROVE"` (or REMOVE/ESCALATE) embedded inside the `"observation"` dict. While the `_build_observation()` method doesn't explicitly expose it, if OpenEnv's framework ever serializes the raw observation data, the agent could see the answer.

**Fix:** Move `ground_truth` out of the `observation` dict to the top-level case dict. In `generate_cases.py`, for every generator function, restructure:

```python
# BEFORE (example from generate_indie_artist):
def generate_indie_artist():
    data = {
        "track_id": f"track-{uuid.uuid4().hex[:12]}",
        "ground_truth": "APPROVE",    # ← INSIDE observation
        "track_title": ...,
        ...
    }
    data.update(_base_fields())
    return {"task_id": "task1", "observation": data}

# AFTER:
def generate_indie_artist():
    obs = {
        "track_id": f"track-{uuid.uuid4().hex[:12]}",
        "track_title": ...,
        ...
    }
    obs.update(_base_fields())
    return {"task_id": "task1", "ground_truth": "APPROVE", "observation": obs}
```

Apply this change to ALL 5 generator functions:
- `generate_indie_artist()` → move `"ground_truth": "APPROVE"` out
- `generate_spammer()` → move `"ground_truth": "REMOVE"` out
- `generate_bot_farm_injection()` → move `"ground_truth": "REMOVE"` out
- `generate_emotional_trap()` → move `"ground_truth": "REMOVE"` out
- `generate_anomalous_genuine()` → move `"ground_truth": "ESCALATE"` out

After changing the generator, **regenerate cases.json**:
```bash
python generate_cases.py
```

Also verify that `server/environment.py`'s `_build_observation()` still works — it uses `case.get("observation", case)` which already handles the nested structure correctly.

---

## 🟡 HIGH FIX 11: `inference.py` should start the environment server or document the requirement clearly

**File:** `inference.py`  
**Problem:** The inference script assumes the environment server is already running at `ENV_URL`. If the hackathon evaluator runs `python inference.py` without starting the server first, it will crash immediately with a connection error.

**Fix:** Add a health-check at the top of `main()` that waits for the server or prints a clear error:

```python
def wait_for_server(url: str, timeout: int = 60) -> None:
    """Wait for the environment server to be ready."""
    import time as _time
    start = _time.time()
    while _time.time() - start < timeout:
        try:
            resp = requests.get(f"{url}/health", timeout=5)
            if resp.status_code == 200:
                return
        except requests.ConnectionError:
            pass
        _time.sleep(2)
    print(f"[ERROR] Server at {url} not reachable after {timeout}s. "
          f"Start it first: uvicorn server.app:app --host 0.0.0.0 --port 7860",
          file=sys.stderr)
    sys.exit(1)
```

Call `wait_for_server(ENV_URL)` at the start of `main()`.

---

## 🟢 MEDIUM FIX 12: Remove unnecessary files from the repo

**Files to delete:**
- `run_server.py` — Redundant. `server/app.py` already has a `main()` entry point, and the Dockerfile uses uvicorn directly.
- `GUIDE.md` — 73KB developer guide not needed for submission. Adds noise.
- `SETUP.md` — 10KB setup guide. The README already has setup instructions.
- `PROJECT_STATUS.md` — Already deleted in latest commit (just confirm it's gone).

**Fix:**
```bash
git rm run_server.py GUIDE.md SETUP.md
git commit -m "chore: remove unnecessary files"
```

---

## 🟢 MEDIUM FIX 13: README should include baseline scores

**File:** `README.md`  
**Problem:** The hackathon requires "README must include: baseline scores." The current README has grading rules but no actual baseline score numbers from running inference.

**Fix:** After running the inference script successfully, add a "Baseline Scores" section to README.md:

```markdown
## 📈 Baseline Scores

Baseline scores using `Qwen/Qwen2.5-72B-Instruct` via HF Router (2 episodes per task):

| Task | Avg Score | Description |
|------|-----------|-------------|
| task1 (Indie Artist) | 0.XXX | Easy — APPROVE |
| task2 (Royalty Farm) | 0.XXX | Easy — REMOVE |
| task3 (Bot + Injection) | 0.XXX | Medium — REMOVE |
| task4 (Emotional Trap) | 0.XXX | Hard — REMOVE |
| task5 (Anomalous Genuine) | 0.XXX | Hard — ESCALATE |
| **Overall** | **0.XXX** | |
```

Replace `0.XXX` with actual numbers from a real inference run.

---

## 🟢 MEDIUM FIX 14: README should include HF Space URL

**File:** `README.md`  
**Problem:** No link to the deployed HF Space.

**Fix:** Add near the top of README:

```markdown
> **Live Demo:** [https://huggingface.co/spaces/<YOUR_USERNAME>/music-content-moderation](https://huggingface.co/spaces/<YOUR_USERNAME>/music-content-moderation)
```

---

## 🟢 MEDIUM FIX 15: `inference.py` default model should be reliable for the HF router

**File:** `inference.py`, line 27  
**Problem:** Default model is `Qwen/Qwen2.5-72B-Instruct`. This model must be available on the HF inference router. If it's unavailable or rate-limited, the inference will fail.

**Fix:** Verify the model works with the HF router. If not, consider a safer default like:
```python
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
```
This is already set. Just verify it works by running:
```bash
export HF_TOKEN="your-token"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
python inference.py
```

---

## 🟢 MEDIUM FIX 16: `openenv.yaml` should use the `state_space` field

**File:** `openenv.yaml`  
**Problem:** The `openenv.yaml` defines `observation_space` and `action_space` but not `state_space`. The OpenEnv spec includes a `state()` endpoint, and the environment does have a `ModerationState` class.

**Fix:** Add to `openenv.yaml` after `action_space`:

```yaml
state_space:
  module: server.models
  class: ModerationState
```

---

## EXECUTION CHECKLIST FOR CLAUDE CODE

Apply changes in this order:

1. ✅ Fix `.gitignore` (Critical Fix 1)
2. ✅ Remove tracked junk from git (Critical Fix 2)  
3. ✅ Fix `num_cases` mismatch (Critical Fix 3)
4. ✅ Clamp step rewards to [0.0, 1.0] (Critical Fix 4)
5. ✅ Update `.dockerignore` (Critical Fix 5)
6. ✅ Add `step_count` to `ModerationState` (High Fix 7)
7. ✅ Reduce `time.sleep` in inference.py (High Fix 8)
8. ✅ Fix version mismatch (High Fix 9)
9. ✅ Move `ground_truth` out of observation data (High Fix 10)
10. ✅ Regenerate `data/cases.json` by running `python generate_cases.py`
11. ✅ Add server health-check to inference.py (High Fix 11)
12. ✅ Remove unnecessary files (Medium Fix 12)
13. ✅ Add `state_space` to openenv.yaml (Medium Fix 16)
14. ✅ Update README with baseline scores placeholder (Medium Fix 13)
15. ✅ Update README with HF Space URL placeholder (Medium Fix 14)
16. 🧑‍💻 MANUAL: Deploy to HF Space (Critical Fix 6)
17. 🧑‍💻 MANUAL: Run inference, capture real baseline scores, update README
18. 🧑‍💻 MANUAL: Run pre-submission validator script
19. ✅ Final git commit and push

---

## VALIDATION COMMANDS (run after all fixes)

```bash
# 1. Verify Docker builds
docker build -t music-moderation .
docker run -d -p 7860:7860 music-moderation

# 2. Verify endpoints
curl -s -X POST http://localhost:7860/reset -H "Content-Type: application/json" -d '{}'
curl -s http://localhost:7860/health
curl -s http://localhost:7860/state

# 3. Verify inference runs
export HF_TOKEN="your-token"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
python inference.py

# 4. Run openenv validate (if installed)
pip install openenv-core
openenv validate

# 5. Run the official pre-submission validator
# (download from hackathon dashboard)
```
