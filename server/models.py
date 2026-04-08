"""
Pydantic models for the Music Content Moderation Environment.
Multi-Step Investigation MDP — Version 2.0

All types inherit from OpenEnv base types for framework compatibility.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from openenv.core.env_server.types import (
    Action as BaseAction,
    Observation as BaseObservation,
    State as BaseState,
)


# ── Observation ──────────────────────────────────────────────────────────────

class ModerationObservation(BaseObservation):
    """
    Partial observation — fields populated progressively via tools.

    On /reset, only the 'always visible' fields are populated.
    Hidden fields start as None and are revealed by INVESTIGATE actions.
    """

    # Always visible
    track_id: str = Field(default="", description="Unique case identifier")
    track_title: str = Field(default="", description="Track name (may contain spam signals)")
    cover_art_desc: str = Field(default="", description="Cover art description (distractor — never decision-relevant)")
    status: str = Field(default="UNDER_REVIEW", description="UNDER_REVIEW or DECIDED")
    step_count: int = Field(default=0, description="Current step in investigation (0-indexed)")
    max_steps: int = Field(default=8, description="Maximum steps allowed per episode")
    available_tools: List[str] = Field(
        default_factory=lambda: ["FETCH_METRICS", "FETCH_ACCOUNT_HISTORY", "FETCH_APPEAL", "FETCH_MARKETING_DATA"],
        description="Tools not yet called in this episode",
    )

    # Revealed by FETCH_METRICS
    duration_ms: Optional[int] = Field(default=None, description="Track duration in milliseconds (revealed by FETCH_METRICS)")
    uploads_last_7d: Optional[int] = Field(default=None, description="Uploads in last 7 days (revealed by FETCH_METRICS)")
    streams_first_24h: Optional[int] = Field(default=None, description="First-24h stream count (revealed by FETCH_METRICS)")
    stream_source_direct_pct: Optional[float] = Field(default=None, description="Direct source stream fraction 0.0-1.0 (revealed by FETCH_METRICS)")

    # Revealed by FETCH_ACCOUNT_HISTORY
    account_age_days: Optional[int] = Field(default=None, description="Account age in days (revealed by FETCH_ACCOUNT_HISTORY)")
    is_verified: Optional[bool] = Field(default=None, description="Verified artist status (revealed by FETCH_ACCOUNT_HISTORY)")
    prior_strikes: Optional[int] = Field(default=None, description="Prior policy strikes (revealed by FETCH_ACCOUNT_HISTORY)")
    algorithmic_playlist_pct: Optional[float] = Field(default=None, description="Algorithmic playlist stream fraction 0.0-1.0 (revealed by FETCH_ACCOUNT_HISTORY)")

    # Revealed by FETCH_APPEAL
    user_appeal_text: Optional[str] = Field(default=None, description="User appeal text if any (revealed by FETCH_APPEAL). Contains emotional manipulation in Task 4, prompt injection in Task 3.")

    # Revealed by FETCH_MARKETING_DATA
    marketing_campaign_active: Optional[bool] = Field(default=None, description="Whether a paid marketing campaign is active (revealed by FETCH_MARKETING_DATA)")

    # Tool call feedback
    last_tool_result: Optional[str] = Field(default=None, description="Feedback string from the last tool call")

    # Episode flags
    investigation_complete: bool = Field(default=False, description="Whether investigation has concluded")


# ── Action ───────────────────────────────────────────────────────────────────

class ModerationAction(BaseAction):
    """
    Agent's action — either INVESTIGATE (call a tool) or DECIDE (make final decision).

    For INVESTIGATE: tool_name is required.
    For DECIDE: decision and cited_signals are required.
    """

    action_type: str = Field(
        ..., description="INVESTIGATE to use a tool, DECIDE to make final decision"
    )

    # For INVESTIGATE actions
    tool_name: Optional[str] = Field(
        default=None,
        description="Tool to call: FETCH_METRICS, FETCH_ACCOUNT_HISTORY, FETCH_APPEAL, FETCH_MARKETING_DATA",
    )

    # For DECIDE actions
    decision: Optional[str] = Field(
        default=None,
        description="Final decision: APPROVE, REMOVE, ESCALATE, RESTORE",
    )
    cited_signals: List[str] = Field(
        default_factory=list,
        description="Observation keys that informed the decision (grader checks these)",
    )
    justification_summary: str = Field(
        default="",
        description="Free-text chain-of-thought reasoning (NOT evaluated by grader)",
    )


# ── State ────────────────────────────────────────────────────────────────────

class ModerationState(BaseState):
    """Internal environment state exposed via /state endpoint."""

    step_count: int = Field(default=0, description="Current step in the episode")
    current_case_index: int = Field(default=0, description="Index of current case in shuffled list")
    total_cases: int = Field(default=0, description="Total cases loaded")
    episode_reward: float = Field(default=0.0, description="Accumulated reward for current episode")
    done: bool = Field(default=False, description="Whether episode is complete")
    revealed_keys: List[str] = Field(default_factory=list, description="Keys revealed via tools so far")
    tools_called: List[str] = Field(default_factory=list, description="Tools called so far")


# ── Constants (used by environment.py and graders.py) ────────────────────────

VALID_OBSERVATION_KEYS: set[str] = {
    "track_id", "track_title", "duration_ms", "cover_art_desc",
    "account_age_days", "is_verified", "uploads_last_7d",
    "streams_first_24h", "stream_source_direct_pct", "algorithmic_playlist_pct",
    "prior_strikes", "user_appeal_text", "marketing_campaign_active",
}

TOOL_REVEALS: dict[str, list[str]] = {
    "FETCH_METRICS": ["duration_ms", "uploads_last_7d", "streams_first_24h", "stream_source_direct_pct"],
    "FETCH_ACCOUNT_HISTORY": ["account_age_days", "is_verified", "prior_strikes", "algorithmic_playlist_pct"],
    "FETCH_APPEAL": ["user_appeal_text"],
    "FETCH_MARKETING_DATA": ["marketing_campaign_active"],
}

VALID_TOOLS: set[str] = set(TOOL_REVEALS.keys())
VALID_DECISIONS: set[str] = {"APPROVE", "REMOVE", "ESCALATE", "RESTORE"}
ALWAYS_VISIBLE_KEYS: set[str] = {"track_id", "track_title", "cover_art_desc"}

MAX_STEPS: int = 8
