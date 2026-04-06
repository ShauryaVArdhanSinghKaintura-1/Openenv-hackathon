"""
Pydantic models for the Music Content Moderation Environment.
Defines Observation and Action spaces per OpenEnv specification.

These inherit from the OpenEnv base types to be compatible with
the create_app() framework.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field

from openenv.core.env_server.types import (
    Action as BaseAction,
    Observation as BaseObservation,
    State as BaseState,
)


# ── Observation Space ────────────────────────────────────────────────────────

class ModerationObservation(BaseObservation):
    """What the agent sees for each moderation case."""

    track_id: str = Field(default="", description="Unique identifier for the track")
    track_title: str = Field(default="", description="Title of the track")
    duration_ms: int = Field(default=0, description="Track duration in milliseconds")
    cover_art_desc: str = Field(
        default="", description="Description of the cover art (distractor signal)"
    )
    account_age_days: int = Field(
        default=0, description="Age of the uploader's account in days"
    )
    is_verified: bool = Field(
        default=False, description="Whether the uploader is a verified artist"
    )
    uploads_last_7d: int = Field(
        default=0, description="Number of tracks uploaded by this account in the last 7 days"
    )
    streams_first_24h: int = Field(
        default=0, description="Number of streams the track received in its first 24 hours"
    )
    stream_source_direct_pct: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Percentage of streams from direct/embedded sources (0.0-1.0)",
    )
    algorithmic_playlist_pct: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Percentage of streams from algorithmic playlists (0.0-1.0)",
    )
    prior_strikes: int = Field(
        default=0, description="Number of prior content-policy strikes on this account"
    )
    user_appeal_text: Optional[str] = Field(
        None,
        description="Optional appeal text submitted by the user (used in Task 3)",
    )


# All valid observation keys for hallucination checking (our domain fields only)
VALID_OBSERVATION_KEYS: set[str] = {
    "track_id", "track_title", "duration_ms", "cover_art_desc",
    "account_age_days", "is_verified", "uploads_last_7d",
    "streams_first_24h", "stream_source_direct_pct", "algorithmic_playlist_pct", 
    "prior_strikes", "user_appeal_text",
}


# ── Action Space ─────────────────────────────────────────────────────────────

class Decision(str, Enum):
    """Possible moderation decisions."""

    APPROVE = "APPROVE"
    REMOVE = "REMOVE"
    ESCALATE = "ESCALATE"
    RESTORE = "RESTORE"


class ModerationAction(BaseAction):
    """What the agent does in response to an observation."""

    decision: Decision = Field(
        ..., description="The moderation decision for this track"
    )
    cited_signals: List[str] = Field(
        default_factory=list,
        description="Exact JSON keys from the observation that informed the decision",
    )
    justification_summary: str = Field(
        default="",
        description=(
            "Free-text chain-of-thought explanation. "
            "IMPORTANT: This field is NOT evaluated by the grader."
        ),
    )


# ── State ────────────────────────────────────────────────────────────────────

class ModerationState(BaseState):
    """Internal environment state."""

    current_case_index: int = Field(default=0, description="Index of current case")
    total_cases: int = Field(default=0, description="Total number of cases in episode")
    total_reward: float = Field(default=0.0, description="Accumulated reward")
    done: bool = Field(default=False, description="Whether the episode is done")


# ── Convenience: Expected signal sets for graders ────────────────────────────

EXPECTED_SIGNALS_TASK1: set[str] = {"duration_ms", "uploads_last_7d", "track_title"}
EXPECTED_SIGNALS_TASK2: set[str] = {"stream_source_direct_pct", "account_age_days"}
EXPECTED_SIGNALS_TASK3: set[str] = {"stream_source_direct_pct", "account_age_days"}


# ── Backward compatibility aliases ──────────────────────────────────────────
# Keep old names working for graders.py and any legacy imports
Observation = ModerationObservation
Action = ModerationAction
