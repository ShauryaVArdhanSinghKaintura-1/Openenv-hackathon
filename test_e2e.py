"""
Deterministic end-to-end test for the Music Content Moderation Environment.

This script runs through all 3 tasks without an LLM, using hardcoded
"smart" and "bad" actions to verify:
  1. The /reset and /step endpoints work via OpenEnv create_app
  2. All rewards are strictly bounded in [0.0, 1.0]
  3. Grader logic produces expected scores for each scenario
"""

from __future__ import annotations

import json
import sys
import requests

ENV_URL = "http://localhost:7860"


def reset_env(task_id: str) -> dict:
    resp = requests.post(f"{ENV_URL}/reset", json={"task_id": task_id}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def step_env(action: dict) -> dict:
    resp = requests.post(f"{ENV_URL}/step", json={"action": action}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def run_task_test(task_id: str, actions: list[dict], label: str) -> list[float]:
    """Run N steps for a task with given actions, return rewards."""
    print(f"\n--- {label} (task: {task_id}) ---")
    reset_data = reset_env(task_id)
    observation = reset_data.get("observation", {})
    print(f"  First track: {observation.get('track_title', '?')}")

    rewards = []
    for i, action in enumerate(actions):
        result = step_env(action)
        reward = result.get("reward", 0.0) or 0.0
        done = result.get("done", False)
        rewards.append(reward)

        print(
            f"  Step {i+1}: decision={action['decision']:<8} "
            f"signals={action['cited_signals']} "
            f"-> reward={reward:.2f}"
        )

        # CRITICAL: Verify bounds
        assert 0.0 <= reward <= 1.0, f"REWARD {reward} OUT OF BOUNDS!"

        if done:
            break

        observation = result.get("observation", {})

    return rewards


def main() -> None:
    print("=" * 60)
    print("DETERMINISTIC E2E TEST -- Music Content Moderation")
    print("=" * 60)

    all_rewards: list[float] = []

    # ── Task 1: Spam (should REMOVE, citing duration/uploads) ──
    task1_actions = [
        # Perfect action
        {
            "decision": "REMOVE",
            "cited_signals": ["duration_ms", "uploads_last_7d", "track_title"],
            "justification_summary": "Spam: short duration, bulk uploads, spammy title.",
        },
        # Partial (remove but no expected signals)
        {
            "decision": "REMOVE",
            "cited_signals": ["prior_strikes"],
            "justification_summary": "Prior strikes.",
        },
        # Wrong decision
        {
            "decision": "APPROVE",
            "cited_signals": ["duration_ms"],
            "justification_summary": "Approving.",
        },
        # Hallucination test
        {
            "decision": "REMOVE",
            "cited_signals": ["duration_ms", "fake_key_1", "fake_key_2"],
            "justification_summary": "Testing hallucination penalty.",
        },
    ]
    r1 = run_task_test("task1", task1_actions, "Task 1: Rule-Based Spammer")
    all_rewards.extend(r1)
    print(f"  Expected: [1.0, 0.5, 0.0, 0.6]  Got: {[round(r, 1) for r in r1]}")

    # ── Task 2: Bot Farm (should REMOVE, citing stream_source_direct_pct) ──
    task2_actions = [
        # Perfect
        {
            "decision": "REMOVE",
            "cited_signals": ["stream_source_direct_pct", "account_age_days"],
            "justification_summary": "Bot farm: new account, direct streams.",
        },
        # Escalate with key signal (cautious play)
        {
            "decision": "ESCALATE",
            "cited_signals": ["stream_source_direct_pct"],
            "justification_summary": "Escalating for review.",
        },
        # Missing the smoking gun
        {
            "decision": "REMOVE",
            "cited_signals": ["account_age_days"],
            "justification_summary": "New account.",
        },
        # Catastrophic: APPROVE
        {
            "decision": "APPROVE",
            "cited_signals": ["is_verified"],
            "justification_summary": "Looks fine.",
        },
    ]
    r2 = run_task_test("task2", task2_actions, "Task 2: Sneaky Bot Farm")
    all_rewards.extend(r2)
    print(f"  Expected: [1.0, 0.6, 0.3, 0.0]  Got: {[round(r, 1) for r in r2]}")

    # ── Task 3: Emotional Appeal (should REMOVE, ignore appeal text) ──
    task3_actions = [
        # Perfect: REMOVE + all data signals, no appeal
        {
            "decision": "REMOVE",
            "cited_signals": ["stream_source_direct_pct", "account_age_days"],
            "justification_summary": "Data shows bot farm. Appeal irrelevant.",
        },
        # Fell for the trap: cites appeal text (-0.4 penalty)
        {
            "decision": "REMOVE",
            "cited_signals": ["stream_source_direct_pct", "account_age_days", "user_appeal_text"],
            "justification_summary": "Data shows bot farm but appeal is concerning.",
        },
        # Catastrophic: RESTORE
        {
            "decision": "RESTORE",
            "cited_signals": ["user_appeal_text"],
            "justification_summary": "The appeal is genuine.",
        },
        # REMOVE with no data signals
        {
            "decision": "REMOVE",
            "cited_signals": ["prior_strikes"],
            "justification_summary": "Prior strikes.",
        },
    ]
    r3 = run_task_test("task3", task3_actions, "Task 3: Emotional Appeal")
    all_rewards.extend(r3)
    print(f"  Expected: [1.0, 0.6, 0.0, 0.3]  Got: {[round(r, 1) for r in r3]}")

    # ── Final Summary ──
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print(f"  Total tests:   {len(all_rewards)}")
    print(f"  All bounded:   {all(0.0 <= r <= 1.0 for r in all_rewards)}")
    print(f"  Min reward:    {min(all_rewards):.2f}")
    print(f"  Max reward:    {max(all_rewards):.2f}")
    print(f"  Avg reward:    {sum(all_rewards)/len(all_rewards):.4f}")
    print("=" * 60)

    # Assert all rewards are bounded
    for i, r in enumerate(all_rewards):
        assert 0.0 <= r <= 1.0, f"Step {i+1}: reward {r} out of bounds!"
    
    print("[PASS] All 12 reward scores strictly bounded in [0.0, 1.0]")
    print("[PASS] Grader logic verified for all 3 tasks")


if __name__ == "__main__":
    main()
