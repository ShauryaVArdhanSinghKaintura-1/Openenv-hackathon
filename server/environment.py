"""
Multi-Step Investigation MDP Environment.

Episode flow:
  1. /reset → Agent gets partial observation (title + metadata only)
  2. /step (INVESTIGATE) → Agent calls a tool, reveals hidden fields, reward +0.05
  3. /step (INVESTIGATE) → More tools...
  4. /step (DECIDE) → Final moderation decision, graded 0.0–0.80, done=True
  5. If step_count >= MAX_STEPS without DECIDE → forced done, reward=0.0

State maintained via module-level globals because OpenEnv's create_app()
creates new Environment instances per HTTP request.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Optional

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import EnvironmentMetadata

from .graders import grade
from .models import (
    ModerationAction,
    ModerationObservation,
    ModerationState,
    TOOL_REVEALS,
    VALID_TOOLS,
    VALID_DECISIONS,
    ALWAYS_VISIBLE_KEYS,
    MAX_STEPS,
)


# ── Data Loading ─────────────────────────────────────────────────────────────

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "cases.json"


def _load_cases() -> list[dict]:
    if not DATA_PATH.exists():
        raise RuntimeError(f"Case data not found at {DATA_PATH}. Run generate_cases.py first.")
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


ALL_CASES = _load_cases()


# ── Module-Level Shared State ────────────────────────────────────────────────
# Required because create_app() instantiates a new Environment per request.
# These globals maintain state across /reset and /step calls.

_cases: list[dict] = []
_case_index: int = 0
_current_case: Optional[dict] = None
_revealed_keys: set[str] = set()
_tools_called: list[str] = []
_step_count: int = 0
_done: bool = True
_episode_reward: float = 0.0


# ── Environment Class ────────────────────────────────────────────────────────

class ModerationEnvironment(
    Environment[ModerationAction, ModerationObservation, ModerationState]
):
    """Music Content Moderation — Multi-Step Investigation MDP."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="Music Content Moderation",
            description=(
                "A Trust & Safety RL environment where agents investigate "
                "music streaming fraud through tool-based evidence gathering "
                "before making a final moderation decision. Features fog-of-war "
                "observations, prompt injection resistance testing, and emotional "
                "manipulation traps."
            ),
            version="2.0.0",
        )

    def _build_observation(self, case: dict) -> ModerationObservation:
        """Build observation with only revealed fields populated."""
        obs_data = case.get("observation", case)

        kwargs: dict[str, Any] = {
            # Always visible
            "track_id": obs_data.get("track_id", ""),
            "track_title": obs_data.get("track_title", ""),
            "cover_art_desc": obs_data.get("cover_art_desc", ""),
            "status": "DECIDED" if _done else "UNDER_REVIEW",
            "step_count": _step_count,
            "max_steps": MAX_STEPS,
            "available_tools": sorted(VALID_TOOLS - set(_tools_called)),
            "investigation_complete": _done,
        }

        # Add last tool feedback
        if _tools_called:
            last = _tools_called[-1]
            count = len(TOOL_REVEALS.get(last, []))
            kwargs["last_tool_result"] = f"{last}: {count} field(s) revealed"

        # Populate only revealed fields
        for key in _revealed_keys:
            if key in obs_data:
                kwargs[key] = obs_data[key]

        return ModerationObservation(**kwargs)

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> ModerationObservation:
        """Reset environment for a new episode."""
        global _cases, _case_index, _current_case, _revealed_keys
        global _tools_called, _step_count, _done, _episode_reward

        if seed is not None:
            random.seed(seed)

        # Filter by task_id if specified
        if task_id:
            _cases = [c for c in ALL_CASES if c["task_id"] == task_id]
        else:
            _cases = list(ALL_CASES)

        if not _cases:
            raise ValueError(f"No cases found for task_id={task_id!r}")

        random.shuffle(_cases)
        _case_index = 0
        _current_case = _cases[0]
        _revealed_keys = set()
        _tools_called = []
        _step_count = 0
        _done = False
        _episode_reward = 0.0

        obs = self._build_observation(_current_case)
        obs.reward = None
        return obs

    def step(
        self,
        action: ModerationAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> ModerationObservation:
        """Process one action (INVESTIGATE or DECIDE)."""
        global _step_count, _done, _current_case, _revealed_keys
        global _tools_called, _episode_reward

        if _done or _current_case is None:
            obs = ModerationObservation(investigation_complete=True)
            obs.done = True
            obs.reward = 0.0
            return obs

        _step_count += 1
        action_type = (action.action_type or "").upper().strip()

        # ── INVESTIGATE ──
        if action_type == "INVESTIGATE":
            tool = (action.tool_name or "").upper().strip()
            reward = 0.0

            if tool not in VALID_TOOLS:
                # Invalid tool — penalty
                reward = -0.05
            elif tool in _tools_called:
                # Duplicate tool call — no reward, no penalty
                reward = 0.0
            else:
                # Valid new tool — reveal fields, reward
                _tools_called.append(tool)
                new_keys = TOOL_REVEALS.get(tool, [])
                _revealed_keys.update(new_keys)
                reward = 0.05

            _episode_reward += reward

            # Check max steps
            if _step_count >= MAX_STEPS:
                _done = True
                obs = self._build_observation(_current_case)
                obs.done = True
                obs.reward = reward
                return obs

            obs = self._build_observation(_current_case)
            obs.done = False
            obs.reward = reward
            return obs

        # ── DECIDE ──
        elif action_type == "DECIDE":
            _done = True
            task_id = _current_case["task_id"]
            decision_str = (action.decision or "").upper().strip()

            if decision_str not in VALID_DECISIONS:
                final_reward = 0.0
            else:
                final_reward = grade(task_id, action, _revealed_keys)

            _episode_reward += final_reward

            obs = self._build_observation(_current_case)
            obs.done = True
            obs.reward = final_reward
            return obs

        # ── UNKNOWN ACTION TYPE ──
        else:
            if _step_count >= MAX_STEPS:
                _done = True

            obs = self._build_observation(_current_case)
            obs.done = _done
            obs.reward = 0.0
            return obs

    @property
    def state(self) -> ModerationState:
        return ModerationState(
            step_count=_step_count,
            current_case_index=_case_index,
            total_cases=len(_cases),
            episode_reward=round(_episode_reward, 4),
            done=_done,
            revealed_keys=sorted(_revealed_keys),
            tools_called=list(_tools_called),
        )

    def close(self) -> None:
        pass
