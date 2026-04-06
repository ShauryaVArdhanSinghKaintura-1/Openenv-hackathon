# 📋 Project Status — Music Content Moderation Environment

> **Last Updated:** April 6, 2026
> **Status:** In Development — Core environment functional, testing in progress

---

## ✅ What Has Been Done

### 1. Core Environment (Complete)
- [x] **OpenEnv-compliant RL environment** built with `create_app()` framework
- [x] FastAPI server with all required endpoints (`/health`, `/metadata`, `/schema`, `/reset`, `/step`, `/state`)
- [x] Pydantic models for `ModerationObservation`, `ModerationAction`, and `ModerationState`
- [x] Stateless HTTP handler design — each `/reset` and `/step` call is self-contained
- [x] Entry point via `server/app.py` using `uvicorn`

### 2. Trust & Safety Taxonomy (Complete)
- [x] Designed and implemented **5 distinct moderation profiles**:
  1. **Indie Artist** — Normal, legitimate user → `APPROVE`
  2. **Spammer Level 1** — Royalty farmer gaming the 30-second rule → `REMOVE`
  3. **Bot Farmer** — High-velocity fake streams from new accounts → `REMOVE`
  4. **Adversarial Spammer** — Bot farmer with emotional manipulation appeal → `REMOVE`
  5. **Anomalous Genuine** — Real viral growth via algorithmic playlists → `ESCALATE`

### 3. Synthetic Data Generator (Complete)
- [x] `generate_cases.py` produces exactly **50 balanced cases** (10 per profile)
- [x] Each case wrapped in `{"task_id": "...", "observation": {...}}` format for environment compatibility
- [x] Profile-specific metric ranges to ensure realistic, non-overlapping data
- [x] `ground_truth` stored in case data for grader access, never exposed to agent
- [x] `algorithmic_playlist_pct` added to observation schema for Task 5

### 4. Deterministic Grading (Complete)
- [x] **5 grading functions** (`grade_task1` through `grade_task5`) — one per profile
- [x] Pure set-math logic, no LLM or regex on justification
- [x] Hallucination penalty: `-0.2` per fabricated signal key
- [x] Emotional trap penalty: `-0.4` for citing `user_appeal_text` in Task 4
- [x] All scores clamped to `[0.0, 1.0]`

### 5. Baseline Inference Script (Complete)
- [x] `inference.py` with OpenRouter/Qwen free-tier LLM integration
- [x] System prompt engineered for Trust & Safety moderation
- [x] JSON response parsing with markdown fence stripping
- [x] Configurable via environment variables (`MODEL_NAME`, `API_BASE_URL`, etc.)

### 6. Infrastructure (Complete)
- [x] `Dockerfile` for Hugging Face Spaces deployment (port 7860)
- [x] `openenv.yaml` environment specification
- [x] `pyproject.toml` with all dependencies
- [x] `requirements.txt` for pip-based installs

---

## 🔧 What Needs to Be Done

### High Priority
- [ ] **Update `test_e2e.py`** — Currently tests only Tasks 1-3 (the old 3-task system). Needs new test cases for Task 4 (Adversarial Spammer) and Task 5 (Anomalous Genuine) to validate the expanded grading logic.
- [ ] **Update `openenv.yaml`** — Currently lists only 3 tasks. Needs Task 4 and Task 5 definitions added to match the 5-profile taxonomy.
- [ ] **Run full integration test** — Start the server, run `test_e2e.py`, and verify all 5 graders produce correct scores.
- [ ] **Run baseline inference** — Execute `inference.py` against the 50-case dataset and collect performance metrics per profile.

### Medium Priority
- [ ] **Align `server/main.py`** — The legacy endpoint file may still reference old 3-task logic. Verify it's consistent or deprecate it.
- [ ] **Add `algorithmic_playlist_pct`** to `openenv.yaml` observation schema — it's in the Pydantic model but missing from the YAML spec.
- [ ] **Rate limit handling** — Add retry/backoff logic to `inference.py` for API rate limits during large runs.
- [ ] **Results logging** — Save inference results (per-task scores, decisions) to a JSON/CSV output file for analysis.

### Low Priority / Nice-to-Have
- [ ] **Visualization** — Build a dashboard or summary script to display per-profile accuracy and reward distributions.
- [ ] **Multi-model benchmarking** — Test against multiple LLMs (GPT-4o, Claude, Gemini) to compare moderation performance.
- [ ] **Hugging Face Spaces deployment** — Push Docker image and verify the environment runs live on HF Spaces.
- [ ] **CI/CD pipeline** — Add GitHub Actions to auto-run `test_e2e.py` on push.

---

## 🧭 Architecture Decisions & Notes for Collaborators

### Key Design Choices

1. **Stateless HTTP Design** — The OpenEnv `create_app()` creates a new environment instance per request. We use module-level shared state (`_shared_cases`, `_shared_step`, etc.) in `environment.py` to maintain episode continuity.

2. **Task ID Mapping** — Each of the 5 profiles maps to a unique `task_id` (`task1`–`task5`). The grader dispatcher in `graders.py` routes to the correct grading function by `task_id`.

3. **Ground Truth Isolation** — `ground_truth` lives in the case JSON for the grader to access, but the `_build_observation()` method in `environment.py` strips it before sending to the agent. The agent never sees the answer.

4. **Hallucination Checking** — If an agent cites a signal key that doesn't exist in `VALID_OBSERVATION_KEYS` (defined in `models.py`), it gets penalized. This prevents the LLM from making up data.

### Running Locally

```bash
# Start the environment server
uv run uvicorn server.app:app --host 0.0.0.0 --port 7860

# In a separate terminal, run tests or inference
python test_e2e.py          # Deterministic tests
python inference.py         # LLM-based inference
python generate_cases.py    # Regenerate dataset
```

### File Dependency Graph

```
generate_cases.py → data/cases.json
                          ↓
server/environment.py ← loads cases.json at import time
         ↓
server/graders.py ← called by environment.step()
         ↓
server/models.py ← Pydantic types used everywhere
         ↓
server/app.py ← FastAPI entry point, creates OpenEnv app
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make changes and test locally
4. Submit a pull request

Please ensure all changes pass the deterministic test suite (`test_e2e.py`) before submitting.
