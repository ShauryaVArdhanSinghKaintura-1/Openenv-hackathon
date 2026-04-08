"""
Standalone test that imports and tests the environment directly,
without requiring the HTTP server to be running.
"""
import sys
import json
from pathlib import Path

# Test imports
print("[TEST] Importing modules...")
try:
    from server.models import (
        ModerationAction,
        ModerationObservation,
        Decision,
        VALID_OBSERVATION_KEYS,
    )
    from server.environment import ModerationEnvironment
    from server.graders import grade
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test environment creation
print("\n[TEST] Creating environment...")
try:
    env = ModerationEnvironment()
    print(f"✓ Environment created: {env.get_metadata().name}")
except Exception as e:
    print(f"✗ Environment creation failed: {e}")
    sys.exit(1)

# Test case loading
print("\n[TEST] Checking case data...")
data_path = Path(__file__).parent / "data" / "cases.json"
if not data_path.exists():
    print(f"✗ cases.json not found at {data_path}")
    sys.exit(1)

with open(data_path) as f:
    cases = json.load(f)
print(f"✓ Loaded {len(cases)} cases")

# Count by task
task_counts = {}
for case in cases:
    task_id = case.get("task_id")
    task_counts[task_id] = task_counts.get(task_id, 0) + 1
print(f"  Distribution: {task_counts}")

# Test reset
print("\n[TEST] Testing environment.reset()...")
try:
    obs = env.reset(task_id="task1", seed=42)
    print(f"✓ Reset successful")
    print(f"  Track: {obs.track_title}")
    print(f"  Duration: {obs.duration_ms}ms")
except Exception as e:
    print(f"✗ Reset failed: {e}")
    sys.exit(1)

# Test step with perfect action
print("\n[TEST] Testing environment.step()...")
try:
    action = ModerationAction(
        decision=Decision.APPROVE,
        cited_signals=["duration_ms", "account_age_days"],
        justification_summary="Test action"
    )
    result = env.step(action)
    reward = result.reward
    print(f"✓ Step successful")
    print(f"  Reward: {reward}")
    print(f"  Done: {result.done}")

    if not (0.0 <= reward <= 1.0):
        print(f"✗ Reward out of bounds: {reward}")
        sys.exit(1)
except Exception as e:
    print(f"✗ Step failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test grading directly
print("\n[TEST] Testing grader functions...")
try:
    test_action = ModerationAction(
        decision=Decision.REMOVE,
        cited_signals=["duration_ms", "uploads_last_7d"],
        justification_summary="Spam"
    )
    score = grade("task2", test_action)
    print(f"✓ Grader returned score: {score}")
    assert 0.0 <= score <= 1.0, f"Score {score} out of bounds"
except Exception as e:
    print(f"✗ Grader failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("[PASS] All standalone tests passed!")
print("=" * 60)
