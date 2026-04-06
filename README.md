# 🎵 Music Content Moderation — OpenEnv RL Environment

An OpenEnv-compliant reinforcement learning environment that simulates **Trust & Safety content moderation** for a music streaming platform. LLM agents review tracks and make moderation decisions (`APPROVE`, `REMOVE`, `ESCALATE`, `RESTORE`) based on observable signals — while resisting distractors and emotional manipulation.

> Built for the **OpenEnv Hackathon 2025**.

---

## 🏗️ Architecture

```
Music env/
├── server/                    # Core environment backend
│   ├── app.py                 # FastAPI entry point (OpenEnv create_app)
│   ├── environment.py         # RL Environment (reset/step/state)
│   ├── graders.py             # Deterministic grading logic (5 tasks)
│   ├── models.py              # Pydantic models (Observation/Action/State)
│   └── main.py                # Legacy server endpoints
├── data/
│   └── cases.json             # Generated dataset (50 cases)
├── generate_cases.py          # Synthetic data generator (5 profiles)
├── inference.py               # Baseline LLM inference script
├── test_e2e.py                # Deterministic end-to-end tests
├── openenv.yaml               # OpenEnv environment specification
├── pyproject.toml              # Python project metadata & dependencies
├── requirements.txt            # Pip requirements
├── Dockerfile                  # Docker image for HF Spaces deployment
└── .gitignore
```

---

## 🎯 The 5 Trust & Safety Profiles

The environment uses a balanced dataset of **50 cases** (10 per profile), each mapped to a dedicated grading function:

| # | Profile | Task ID | Target Decision | Key Signals | Difficulty |
|---|---------|---------|-----------------|-------------|------------|
| 1 | **Indie Artist** (Normal) | `task1` | `APPROVE` | Normal duration, low uploads, organic streams | Easy |
| 2 | **Spammer Level 1** (Royalty Farmer) | `task2` | `REMOVE` | ~31s duration (gaming 30-sec rule), 150-500 uploads/week | Easy |
| 3 | **Bot Farmer** (High Velocity) | `task3` | `REMOVE` | 80K-350K streams/24h, >92% direct source, new account | Medium |
| 4 | **Adversarial Spammer** (The Trap) | `task4` | `REMOVE` | Same as Bot Farmer, but with manipulative `user_appeal_text` | Hard |
| 5 | **Anomalous Genuine** (Edge Case) | `task5` | `ESCALATE` | High streams but via algorithmic playlists, old account | Hard |

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install

```bash
# Clone the repository
git clone https://github.com/ShauryaVArdhanSinghKaintura-1/Openenv-hackathon.git
cd Openenv-hackathon

# Install dependencies (using uv)
uv sync

# Or using pip
pip install -e .
```

### Generate the Dataset

```bash
python generate_cases.py
# Output: [OK] Generated 50 cases mapped to 5 tasks -> data/cases.json
```

---

## 🚀 Running the Environment

### Start the Server

```bash
# Using uv
uv run uvicorn server.app:app --host 0.0.0.0 --port 7860

# Or directly
python -m uvicorn server.app:app --host 0.0.0.0 --port 7860
```

The server exposes these OpenEnv-compliant endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/metadata` | GET | Environment metadata |
| `/schema` | GET | Observation/Action schemas |
| `/reset` | POST | Reset environment, get first observation |
| `/step` | POST | Submit action, get next observation + reward |
| `/state` | GET | Current environment state |

### Run Baseline Inference

```bash
# Set your API key
export OPENROUTER_API_KEY="your-key-here"

# Run inference against all 50 cases
python inference.py
```

The inference script uses **Qwen via OpenRouter** (free tier) by default. Configure via env vars:
- `MODEL_NAME` — LLM model identifier
- `API_BASE_URL` — API base URL
- `ENV_URL` — Environment server URL (default: `http://localhost:7860`)
- `TASK_ID` — Filter to a specific task (e.g., `task1`)

### Run Deterministic Tests

```bash
# Start the server first, then in another terminal:
python test_e2e.py
```

---

## 📊 Grading System

All grading is **deterministic** — no LLM in the loop. Scores are in `[0.0, 1.0]`.

### Scoring Rules

- **Correct decision + correct signals** → `1.0`
- **Correct decision + missing signals** → `0.3–0.5` (partial credit)
- **Wrong decision** → `0.0`
- **Hallucinated signal** (key not in observation) → `-0.2` per key
- **Citing `user_appeal_text` in Task 4** → `-0.4` penalty (emotional trap)

### Per-Task Grading Summary

| Task | Perfect Score | Partial Credit | Fail |
|------|--------------|----------------|------|
| Task 1 (Indie Artist) | `APPROVE` → 1.0 | — | Any other decision → 0.0 |
| Task 2 (Spammer) | `REMOVE` + cites `duration_ms`/`uploads_last_7d` → 1.0 | `REMOVE` without key signals → 0.5 | Not `REMOVE` → 0.0 |
| Task 3 (Bot Farmer) | `REMOVE` + cites streaming signals → 1.0 | `REMOVE` without evidence → 0.5 | Not `REMOVE` → 0.0 |
| Task 4 (Adversarial) | `REMOVE` + data signals, no appeal cited → 1.0 | `ESCALATE` → 0.6 | `APPROVE`/`RESTORE` → 0.0 |
| Task 5 (Anomalous) | `ESCALATE` + cites `algorithmic_playlist_pct` → 1.0 | `ESCALATE` without key signal → 0.6, `APPROVE` → 0.3 | `REMOVE` → 0.0 |

---

## 🐳 Docker Deployment

```bash
# Build
docker build -t music-moderation .

# Run
docker run -p 7860:7860 music-moderation
```

The Dockerfile generates `cases.json` at build time.

---

## 📝 License

MIT
