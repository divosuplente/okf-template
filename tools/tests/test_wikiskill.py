"""Unit tests for wikiskill.py pure functions."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import wikiskill


def test_sample_traces():
    traces = [
        {"task_id": f"t{i}", "passed": i % 2 == 0, "trace": "x" * (100 - i)}
        for i in range(20)
    ]
    sampled = wikiskill.sample_traces(traces, max_failing=5, max_passing=3)
    failing = [t for t in sampled if not t["passed"]]
    passing = [t for t in sampled if t["passed"]]
    assert len(failing) == 5
    assert len(passing) == 3
    assert len(sampled) == 8


def test_sample_traces_truncation():
    long_trace = "A" * 20000
    traces = [{"task_id": "big", "passed": False, "trace": long_trace}]
    sampled = wikiskill.sample_traces(traces, char_cap=15000)
    assert len(sampled[0]["trace"]) == 15000 + len("...[truncated]")
    assert sampled[0]["trace"].endswith("...[truncated]")


def test_sample_traces_empty():
    assert wikiskill.sample_traces([]) == []


def test_default_scorer_exact_match():
    task = {"expected": "Paris", "description": "What is the capital of France?"}
    assert wikiskill.default_scorer(task, "The answer is Paris") == 1.0


def test_default_scorer_case_insensitive():
    task = {"expected": "paris"}
    assert wikiskill.default_scorer(task, "ANSWER: PARIS") == 1.0


def test_default_scorer_no_match():
    task = {"expected": "London"}
    assert wikiskill.default_scorer(task, "The answer is Paris") == 0.0


def test_default_scorer_no_expected_key():
    task = {"description": "Solve this problem"}
    assert wikiskill.default_scorer(task, "anything") == 0.5


def test_apply_patch_append():
    content = "line1\nline2\n"
    result = wikiskill.apply_patch(content, "append", "line1\n", "inserted\n")
    assert "line1\ninserted\nline2\n" == result


def test_apply_patch_replace():
    content = "old line\nline2\n"
    result = wikiskill.apply_patch(content, "replace", "old line", "new line")
    assert "new line\nline2\n" == result


def test_apply_patch_insert_after():
    content = "header\nbody\n"
    result = wikiskill.apply_patch(content, "insert_after", "header\n", "middle\n")
    assert "header\nmiddle\nbody\n" == result


def test_apply_patch_target_not_found():
    try:
        wikiskill.apply_patch("hello", "append", "notpresent", "x")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "not found" in str(e)


def test_apply_patch_unknown_op():
    try:
        wikiskill.apply_patch("hello", "delete", "hel", "x")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "unknown op" in str(e)


def test_generate_diff():
    old = "line1\nline2\nline3\n"
    new = "line1\nchanged\nline3\n"
    diff = wikiskill.generate_diff(old, new)
    assert "--- a/SKILL.md" in diff
    assert "+++ b/SKILL.md" in diff
    assert "-line2" in diff
    assert "+changed" in diff


def test_load_scorer_default():
    fn = wikiskill.load_scorer(None)
    assert fn is wikiskill.default_scorer


def test_load_scorer_custom():
    fn = wikiskill.load_scorer("wikiskill:default_scorer")
    assert fn is wikiskill.default_scorer


def test_init_workspace(tmp_path):
    ws = wikiskill.init_workspace(str(tmp_path / "ws"))
    assert (ws / "raw" / "traces").is_dir()
    assert (ws / "wiki" / "patterns").is_dir()
    assert (ws / "wiki" / "index.md").exists()
    assert (ws / "wiki" / "logs.md").exists()
    assert (ws / "wiki" / "skill-impact.md").exists()
    assert (ws / "skills").is_dir()
    assert (ws / "state.json").exists()

    state = json.loads((ws / "state.json").read_text())
    assert state["iteration"] == 0
    assert state["r_best"] == 0.0
    assert state["history"] == []


def test_state_round_trip(tmp_path):
    ws = str(tmp_path / "ws")
    wikiskill.init_workspace(ws)
    state = {"iteration": 3, "r_best": 0.75, "history": [{"k": 1, "r_val": 0.5, "accepted": True}]}
    wikiskill.save_state(ws, state)
    loaded = wikiskill.load_state(ws)
    assert loaded == state
