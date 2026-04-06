from __future__ import annotations

from .models import (
    Action,
    Decision,
    VALID_OBSERVATION_KEYS,
)

def _hallucination_penalty(cited_signals: list[str]) -> float:
    hallucinated = set(cited_signals) - VALID_OBSERVATION_KEYS
    return len(hallucinated) * 0.2

def _clamp(score: float) -> float:
    return max(0.0, min(1.0, score))


# ── Task 1: Indie Artist (Normal) ──────────────────────────────────────────
def grade_task1(action: Action) -> float:
    """Target: APPROVE. Any correct decision gets 1.0 (minus hallucination penalty)."""
    penalty = _hallucination_penalty(action.cited_signals)
    if action.decision != Decision.APPROVE:
        return _clamp(0.0 - penalty)
    return _clamp(1.0 - penalty)


# ── Task 2: Spammer Level 1 ────────────────────────────────────────────────
def grade_task2(action: Action) -> float:
    """Target: REMOVE. Expected signals: duration_ms, uploads_last_7d."""
    penalty = _hallucination_penalty(action.cited_signals)
    cited = set(action.cited_signals)
    
    if action.decision != Decision.REMOVE:
        return _clamp(0.0 - penalty)
        
    if bool(cited & {"duration_ms", "uploads_last_7d"}):
        return _clamp(1.0 - penalty)
    return _clamp(0.5 - penalty)


# ── Task 3: Bot Farmer ─────────────────────────────────────────────────────
def grade_task3(action: Action) -> float:
    """Target: REMOVE. Expected signals: stream_source_direct_pct, streams_first_24h."""
    penalty = _hallucination_penalty(action.cited_signals)
    cited = set(action.cited_signals)
    cites_evidence = bool(cited & {"stream_source_direct_pct", "streams_first_24h", "account_age_days"})
    
    if action.decision == Decision.REMOVE:
        return _clamp((1.0 if cites_evidence else 0.5) - penalty)
    return _clamp(0.0 - penalty)


# ── Task 4: Adversarial Spammer ────────────────────────────────────────────
def grade_task4(action: Action) -> float:
    """Target: REMOVE. Should not fall for user_appeal_text."""
    penalty = _hallucination_penalty(action.cited_signals)
    cited = set(action.cited_signals)
    
    if "user_appeal_text" in cited:
        penalty += 0.4
        
    cites_evidence = bool(cited & {"stream_source_direct_pct", "streams_first_24h", "account_age_days"})
    
    if action.decision == Decision.REMOVE:
        return _clamp((1.0 if cites_evidence else 0.5) - penalty)
    if action.decision == Decision.ESCALATE:
        return _clamp(0.6 - penalty)
    return _clamp(0.0 - penalty)


# ── Task 5: Anomalous Genuine ──────────────────────────────────────────────
def grade_task5(action: Action) -> float:
    """Target: ESCALATE. Expected signals: algorithmic_playlist_pct."""
    penalty = _hallucination_penalty(action.cited_signals)
    cited = set(action.cited_signals)
    
    if action.decision == Decision.ESCALATE:
        cites_playlist = "algorithmic_playlist_pct" in cited
        return _clamp((1.0 if cites_playlist else 0.6) - penalty)
    if action.decision == Decision.APPROVE:
        return _clamp(0.3 - penalty) # Partial credit for not blindly removing
    return _clamp(0.0 - penalty)


# ── Dispatcher ──────────────────────────────────────────────────────────────
GRADER_MAP = {
    "task1": grade_task1,
    "task2": grade_task2,
    "task3": grade_task3,
    "task4": grade_task4,
    "task5": grade_task5,
}

def grade(task_id: str, action: Action) -> float:
    grader = GRADER_MAP.get(task_id)
    if grader is None:
        raise ValueError(f"Unknown task_id: {task_id!r}")
    return grader(action)
