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


def test_safe_name_rejects_traversal():
    assert wikiskill._safe_name("../../etc/passwd") == "unnamed"
    assert wikiskill._safe_name("foo/bar") == "unnamed"
    assert wikiskill._safe_name("foo\\bar") == "unnamed"
    assert wikiskill._safe_name("..") == "unnamed"
    assert wikiskill._safe_name("") == "unnamed"
    assert wikiskill._safe_name(None) == "unnamed"
    assert wikiskill._safe_name("good-name") == "good-name"
    assert wikiskill._safe_name("good_name") == "good_name"


def test_safe_name_custom_fallback():
    assert wikiskill._safe_name("../bad", "default") == "default"
    assert wikiskill._safe_name("ok", "default") == "ok"


def _setup_ws(tmp_path):
    """Create an initialized workspace for tests."""
    ws = str(tmp_path / "ws")
    wikiskill.init_workspace(ws)
    return ws


def test_run_iteration_accept(tmp_path):
    """Mock agent_fn returns correct answers → iteration accepted."""
    ws = _setup_ws(tmp_path)
    train = [{"id": "t1", "description": "What is 2+2?", "expected": "4"}]

    # agent_fn returns: inference → "ANSWER: 4", proposer → no_action JSON, validation → "ANSWER: 2"
    call_count = [0]
    def mock_agent(prompt):
        call_count[0] += 1
        if "Skill Proposer" in prompt:
            return '{"action": "no_action", "summary": "skip"}'
        return "ANSWER: 4"

    # completion_fn returns wiki maintainer JSON
    def mock_completion(prompt):
        return '{"patterns": [], "log_entry": "noop"}'

    result = wikiskill.run_iteration(
        ws, iteration=1, train_tasks=train,
        val_tasks=[{"id": "v1", "description": "What is 2+2?", "expected": "4"}],
        scorer_fn=wikiskill.default_scorer,
        agent_fn=mock_agent, completion_fn=mock_completion,
    )
    assert result["accepted"] is True
    assert result["r_val"] >= 0.5
    assert result["r_best"] >= 0.5
    state = wikiskill.load_state(ws)
    assert state["history"][-1]["accepted"] is True


def test_run_iteration_reject_rollback(tmp_path):
    """Mock agent_fn returns wrong answers → iteration rejected, skills rolled back."""
    ws = _setup_ws(tmp_path)
    train = [{"id": "t1", "description": "What is 2+2?", "expected": "4"}]

    def mock_agent(prompt):
        if "Skill Proposer" in prompt:
            return '{"action": "no_action", "summary": "skip"}'
        # Return wrong answer for both train and val
        return "ANSWER: 99"

    def mock_completion(prompt):
        return '{"patterns": [], "log_entry": "noop"}'

    result = wikiskill.run_iteration(
        ws, iteration=1, train_tasks=train,
        val_tasks=[{"id": "v1", "description": "What is 2+2?", "expected": "4"}],
        scorer_fn=wikiskill.default_scorer,
        agent_fn=mock_agent, completion_fn=mock_completion,
    )
    assert result["accepted"] is False
    assert result["r_val"] == 0.0
    assert result["r_best"] == 0.0
    state = wikiskill.load_state(ws)
    assert state["history"][-1]["accepted"] is False


def test_validate_tasks_basic(tmp_path):
    """Unit test for _validate_tasks helper."""
    ws = str(tmp_path / "ws")
    wikiskill.init_workspace(ws)
    val_tasks = [
        {"id": "v1", "description": "What is 2+2?", "expected": "4"},
        {"id": "v2", "description": "Capital of France?", "expected": "Paris"},
    ]

    def mock_agent(prompt):
        return "ANSWER: wrong"

    traces, r_val = wikiskill._validate_tasks(ws, val_tasks, wikiskill.default_scorer, mock_agent)
    assert r_val == 0.0
    assert len(traces) == 2
    assert all(t["passed"] is False for t in traces)

    def mock_agent_correct(prompt):
        return "ANSWER: 4"

    traces2, r_val2 = wikiskill._validate_tasks(ws, val_tasks, wikiskill.default_scorer, mock_agent_correct)
    assert r_val2 == 0.5  # one of two correct
