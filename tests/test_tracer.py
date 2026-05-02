import json
import sqlite3
import pytest
from pathlib import Path
from observability.tracer import NullTracer, Tracer, _compute_cost
from observability.inspect import inspect_run


def test_compute_cost_sonnet():
    cost = _compute_cost("claude-sonnet-4-6", 1_000_000, 1_000_000)
    assert abs(cost - 18.00) < 0.001  # $3.00 in + $15.00 out


def test_compute_cost_haiku():
    cost = _compute_cost("claude-haiku-4-5-20251001", 1_000_000, 1_000_000)
    assert abs(cost - 4.80) < 0.001  # $0.80 in + $4.00 out


def test_compute_cost_unknown_model_defaults_to_sonnet():
    cost = _compute_cost("unknown-model", 1_000_000, 0)
    assert abs(cost - 3.00) < 0.001


def test_null_tracer_is_no_op():
    t = NullTracer()
    t.start_run("run1", "query")
    t.record_clarification("q", "a")
    t.record_routing("research", "web lookup")
    t.record_node_start("researcher")
    t.record_llm_call("researcher", "claude-sonnet-4-6", 100, 50, 1500)
    t.record_tool_call("search", {"query": "test"}, 200)
    t.finish_run("answer", 3000)
    # No error, no DB created — passes by not raising


@pytest.fixture
def tmp_tracer(tmp_path):
    return Tracer(db_path=tmp_path / "test.db")


def test_tracer_creates_db(tmp_path):
    Tracer(db_path=tmp_path / "test.db")
    assert (tmp_path / "test.db").exists()


def test_tracer_start_run_inserts_row(tmp_tracer):
    tmp_tracer.start_run("run-123", "what is langgraph?")
    with sqlite3.connect(tmp_tracer._db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM runs WHERE id = ?", ("run-123",)).fetchone()
    assert row["query"] == "what is langgraph?"
    assert row["timestamp"] is not None
    assert "T" in row["timestamp"] and row["timestamp"].endswith("Z")


def test_tracer_record_node_start_inserts_event(tmp_tracer):
    tmp_tracer.start_run("run-123", "query")
    tmp_tracer.record_node_start("researcher")
    with sqlite3.connect(tmp_tracer._db_path) as conn:
        conn.row_factory = sqlite3.Row
        events = conn.execute("SELECT * FROM events WHERE run_id = ?", ("run-123",)).fetchall()
    assert len(events) == 1
    assert events[0]["event_type"] == "node_start"
    assert events[0]["name"] == "researcher"


def test_tracer_record_llm_call_inserts_node_end(tmp_tracer):
    tmp_tracer.start_run("run-123", "query")
    tmp_tracer.record_llm_call("researcher", "claude-sonnet-4-6", 1000, 200, 2000)
    with sqlite3.connect(tmp_tracer._db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM events WHERE run_id = ? AND event_type = 'node_end'",
            ("run-123",)
        ).fetchone()
    assert row["name"] == "researcher"
    assert row["input_tokens"] == 1000
    assert row["output_tokens"] == 200
    assert row["duration_ms"] == 2000
    assert row["cost_usd"] is not None and row["cost_usd"] > 0


def test_tracer_record_tool_call_inserts_event(tmp_tracer):
    tmp_tracer.start_run("run-123", "query")
    tmp_tracer.record_tool_call("search", {"query": "LangGraph"}, 350)
    with sqlite3.connect(tmp_tracer._db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM events WHERE run_id = ? AND event_type = 'tool_call'",
            ("run-123",)
        ).fetchone()
    assert row["name"] == "search"
    assert row["duration_ms"] == 350
    detail = json.loads(row["detail"])
    assert detail["input"] == {"query": "LangGraph"}
    assert detail["denied"] is False


def test_tracer_record_tool_call_denied(tmp_tracer):
    tmp_tracer.start_run("run-123", "query")
    tmp_tracer.record_tool_call("read_file", {"path": "/etc/passwd"}, 0, denied=True)
    with sqlite3.connect(tmp_tracer._db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM events WHERE run_id = ? AND event_type = 'tool_call'",
            ("run-123",)
        ).fetchone()
    assert json.loads(row["detail"])["denied"] is True


def test_tracer_finish_run_updates_totals(tmp_tracer):
    tmp_tracer.start_run("run-123", "query")
    tmp_tracer.record_routing("research", "web lookup needed")
    tmp_tracer.record_llm_call("researcher", "claude-sonnet-4-6", 1000, 200, 2000)
    tmp_tracer.record_llm_call("summarizer", "claude-sonnet-4-6", 500, 100, 1000)
    tmp_tracer.finish_run("final answer here", 5000)
    with sqlite3.connect(tmp_tracer._db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM runs WHERE id = ?", ("run-123",)).fetchone()
    assert row["final_answer"] == "final answer here"
    assert row["duration_ms"] == 5000
    assert row["route"] == "research"
    assert row["total_input_tokens"] == 1500
    assert row["total_output_tokens"] == 300
    assert row["total_cost_usd"] is not None and row["total_cost_usd"] > 0


def test_tracer_events_have_sequential_seq(tmp_tracer):
    tmp_tracer.start_run("run-123", "query")
    tmp_tracer.record_node_start("supervisor")
    tmp_tracer.record_routing("research", "web")
    tmp_tracer.record_node_start("researcher")
    with sqlite3.connect(tmp_tracer._db_path) as conn:
        seqs = [r[0] for r in conn.execute(
            "SELECT seq FROM events WHERE run_id = ? ORDER BY seq", ("run-123",)
        ).fetchall()]
    assert seqs == [1, 2, 3]


def test_tracer_seq_resets_on_second_start_run(tmp_tracer):
    tmp_tracer.start_run("run-001", "first query")
    tmp_tracer.record_node_start("researcher")
    tmp_tracer.record_node_start("summarizer")
    tmp_tracer.start_run("run-002", "second query")
    tmp_tracer.record_node_start("supervisor")
    with sqlite3.connect(tmp_tracer._db_path) as conn:
        seqs = [r[0] for r in conn.execute(
            "SELECT seq FROM events WHERE run_id = ? ORDER BY seq", ("run-002",)
        ).fetchall()]
    assert seqs == [1]


# ── Inspect ──────────────────────────────────────────────────────────────────


def _seed_db(tmp_tracer):
    """Seed a complete run for inspect tests."""
    tmp_tracer.start_run("abc12345", "How does auth work?")
    tmp_tracer.record_routing("codebase", "exploring local code")
    tmp_tracer.record_node_start("researcher")
    tmp_tracer.record_tool_call("list_directory", {"path": "."}, 120)
    tmp_tracer.record_tool_call("read_file", {"path": "/etc/passwd"}, 0, denied=True)
    tmp_tracer.record_llm_call("researcher", "claude-sonnet-4-6", 1842, 312, 3200)
    tmp_tracer.record_node_start("summarizer")
    tmp_tracer.record_llm_call("summarizer", "claude-sonnet-4-6", 2104, 489, 2900)
    tmp_tracer.finish_run("Auth uses JWT tokens.", 8300)


def test_inspect_run_prints_header(tmp_tracer, capsys):
    _seed_db(tmp_tracer)
    inspect_run("abc12345", tmp_tracer._db_path)
    out = capsys.readouterr().out
    assert "abc12345" in out
    assert "codebase" in out
    assert "8.3s" in out
    assert "$" in out


def test_inspect_run_prints_timeline(tmp_tracer, capsys):
    _seed_db(tmp_tracer)
    inspect_run("abc12345", tmp_tracer._db_path)
    out = capsys.readouterr().out
    assert "researcher" in out
    assert "list_directory" in out
    assert "[denied]" in out
    assert "summarizer" in out


def test_inspect_run_prints_summary(tmp_tracer, capsys):
    _seed_db(tmp_tracer)
    inspect_run("abc12345", tmp_tracer._db_path)
    out = capsys.readouterr().out
    assert "Route:" in out
    assert "Tokens:" in out
    assert "Cost:" in out
    assert "Answer:" in out
    assert "Auth uses JWT" in out


def test_inspect_run_unknown_id(tmp_tracer, capsys):
    inspect_run("nonexistent", tmp_tracer._db_path)
    out = capsys.readouterr().out
    assert "No run found" in out


def test_inspect_run_last(tmp_tracer, capsys):
    _seed_db(tmp_tracer)
    inspect_run("last", tmp_tracer._db_path)
    out = capsys.readouterr().out
    assert "abc12345" in out
