"""
FastAPI server for the Music Content Moderation OpenEnv Environment.

Endpoints:
    POST /reset   — Reset the environment (optionally to a specific task).
    POST /step    — Submit an action, receive reward + next observation.
    POST /state   — Return the current environment state.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .graders import grade
from .models import Action, Decision, Observation

# ── Load cases ──────────────────────────────────────────────────────────────

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "cases.json"


def _load_cases() -> list[dict]:
    if not DATA_PATH.exists():
        raise RuntimeError(
            f"Case data not found at {DATA_PATH}. Run generate_cases.py first."
        )
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


ALL_CASES = _load_cases()

# ── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Music Content Moderation Environment",
    description="OpenEnv-compliant RL environment for Trust & Safety moderation.",
    version="1.0.0",
)


# ── Episode State ───────────────────────────────────────────────────────────


class EpisodeState:
    """Tracks the state of the current episode."""

    def __init__(self) -> None:
        self.cases: list[dict] = []
        self.current_step: int = 0
        self.task_id: Optional[str] = None
        self.done: bool = True
        self.total_reward: float = 0.0
        self.step_rewards: list[float] = []

    def reset(self, task_id: Optional[str] = None) -> dict:
        """Reset to a new episode, optionally filtered by task_id."""
        if task_id:
            self.cases = [c for c in ALL_CASES if c["task_id"] == task_id]
        else:
            self.cases = list(ALL_CASES)

        if not self.cases:
            raise ValueError(f"No cases found for task_id={task_id!r}")

        random.shuffle(self.cases)
        self.current_step = 0
        self.task_id = task_id
        self.done = False
        self.total_reward = 0.0
        self.step_rewards = []
        return self.current_observation()

    def current_observation(self) -> dict:
        if self.done or self.current_step >= len(self.cases):
            return {}
        return self.cases[self.current_step]["observation"]

    def current_task_id(self) -> str:
        return self.cases[self.current_step]["task_id"]

    def step(self, action: Action) -> dict:
        if self.done:
            raise RuntimeError("Episode is done. Call /reset first.")

        task_id = self.current_task_id()
        reward = grade(task_id, action)
        self.total_reward += reward
        self.step_rewards.append(reward)
        self.current_step += 1

        if self.current_step >= len(self.cases):
            self.done = True

        return {
            "reward": reward,
            "done": self.done,
            "total_reward": self.total_reward,
            "steps_completed": self.current_step,
            "steps_remaining": max(0, len(self.cases) - self.current_step),
            "observation": self.current_observation(),
        }


# Singleton episode state
_state = EpisodeState()


# ── Request / Response Models ───────────────────────────────────────────────


class ResetRequest(BaseModel):
    task_id: Optional[str] = None


class StepRequest(BaseModel):
    decision: str
    cited_signals: list[str]
    justification_summary: str


class StateResponse(BaseModel):
    current_step: int
    total_steps: int
    done: bool
    total_reward: float
    observation: dict[str, Any]


# ── Endpoints ───────────────────────────────────────────────────────────────


@app.post("/reset")
def reset(req: ResetRequest = ResetRequest()):
    """Reset the environment and return the first observation."""
    try:
        obs = _state.reset(task_id=req.task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "observation": obs,
        "total_steps": len(_state.cases),
        "message": "Environment reset successfully.",
    }


@app.post("/step")
def step(req: StepRequest):
    """Submit a moderation action and receive the reward + next observation."""
    if _state.done:
        raise HTTPException(
            status_code=400, detail="Episode is done. Call /reset first."
        )

    # Convert the request into a proper Action
    try:
        decision = Decision(req.decision)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid decision: {req.decision!r}. Must be one of: {[d.value for d in Decision]}",
        )

    action = Action(
        decision=decision,
        cited_signals=req.cited_signals,
        justification_summary=req.justification_summary,
    )

    try:
        result = _state.step(action)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return result


@app.post("/state")
def state():
    """Return the current environment state."""
    return StateResponse(
        current_step=_state.current_step,
        total_steps=len(_state.cases),
        done=_state.done,
        total_reward=_state.total_reward,
        observation=_state.current_observation(),
    ).model_dump()


@app.get("/")
def root():
    """Health check / info endpoint."""
    return {
        "name": "Music Content Moderation Environment",
        "version": "1.0.0",
        "status": "running",
        "endpoints": ["/reset", "/step", "/state"],
    }
