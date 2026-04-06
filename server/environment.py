"""
Music Content Moderation Environment -- OpenEnv Environment implementation.

Implements the Environment base class with reset(), step(), and state.

DESIGN NOTE: The OpenEnv HTTP server (create_app) creates a NEW environment
instance for each /reset and /step call. Therefore this environment uses a
stateless, single-step design:
  - reset() picks one random case and stores it
  - step() grades the action against that stored case
  - Each HTTP call is self-contained

For multi-step episodes (e.g. inference.py baseline), use the legacy
server/main.py endpoints directly.
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
    Decision,
    ModerationAction,
    ModerationObservation,
    ModerationState,
)


# -- Load cases --------------------------------------------------------------

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "cases.json"

# Module-level shared state for multi-step HTTP episodes
_shared_cases: list[dict] = []
_shared_step: int = 0
_shared_done: bool = True
_shared_total_reward: float = 0.0
_shared_current_case: Optional[dict] = None


def _load_cases() -> list[dict]:
    if not DATA_PATH.exists():
        raise RuntimeError(
            f"Case data not found at {DATA_PATH}. Run generate_cases.py first."
        )
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


ALL_CASES = _load_cases()


# -- Environment --------------------------------------------------------------

class ModerationEnvironment(
    Environment[ModerationAction, ModerationObservation, ModerationState]
):
    """
    Music Content Moderation RL Environment.

    Uses module-level shared state so that the stateless HTTP handler
    (which creates a new instance per request) can maintain episode
    continuity across /reset and /step calls.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="Music Content Moderation",
            description=(
                "An RL environment simulating Trust & Safety content moderation "
                "for a music streaming platform. Agents must review tracks and "
                "make moderation decisions based on observable signals."
            ),
            version="1.0.0",
        )

    def _build_observation(self, case_data: dict, done: bool = False, reward: float | None = None) -> ModerationObservation:
        """Build a ModerationObservation from raw case data, stripping task_id."""
        obs_data = case_data.get("observation", case_data)
        return ModerationObservation(
            track_id=obs_data.get("track_id", ""),
            track_title=obs_data.get("track_title", ""),
            duration_ms=obs_data.get("duration_ms", 0),
            cover_art_desc=obs_data.get("cover_art_desc", ""),
            account_age_days=obs_data.get("account_age_days", 0),
            is_verified=obs_data.get("is_verified", False),
            uploads_last_7d=obs_data.get("uploads_last_7d", 0),
            streams_first_24h=obs_data.get("streams_first_24h", 0),
            stream_source_direct_pct=obs_data.get("stream_source_direct_pct", 0.0),
            prior_strikes=obs_data.get("prior_strikes", 0),
            user_appeal_text=obs_data.get("user_appeal_text"),
            done=done,
            reward=reward,
        )

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> ModerationObservation:
        """Reset environment, optionally filtering to a specific task."""
        global _shared_cases, _shared_step, _shared_done
        global _shared_total_reward, _shared_current_case

        if seed is not None:
            random.seed(seed)

        if task_id:
            _shared_cases = [c for c in ALL_CASES if c["task_id"] == task_id]
        else:
            _shared_cases = list(ALL_CASES)

        if not _shared_cases:
            raise ValueError(f"No cases found for task_id={task_id!r}")

        random.shuffle(_shared_cases)
        _shared_step = 0
        _shared_done = False
        _shared_total_reward = 0.0
        _shared_current_case = _shared_cases[0]

        return self._build_observation(_shared_current_case, done=False)

    def step(
        self,
        action: ModerationAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> ModerationObservation:
        """Process a moderation action and return the next observation."""
        global _shared_step, _shared_done, _shared_total_reward, _shared_current_case

        if _shared_done or _shared_current_case is None:
            return ModerationObservation(done=True, reward=0.0)

        # Grade using the internal task_id (never exposed to agent)
        task_id = _shared_current_case["task_id"]
        reward = grade(task_id, action)
        _shared_total_reward += reward
        _shared_step += 1

        if _shared_step >= len(_shared_cases):
            _shared_done = True
            _shared_current_case = None
            return ModerationObservation(done=True, reward=reward)

        # Advance to next case
        _shared_current_case = _shared_cases[_shared_step]
        obs = self._build_observation(_shared_current_case, done=False, reward=reward)
        return obs

    @property
    def state(self) -> ModerationState:
        """Get current environment state."""
        return ModerationState(
            step_count=_shared_step,
            current_case_index=_shared_step,
            total_cases=len(_shared_cases),
            total_reward=_shared_total_reward,
            done=_shared_done,
        )

    def close(self) -> None:
        """Clean up resources (no-op since state is module-level)."""
        pass
