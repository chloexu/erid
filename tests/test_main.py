"""Tests for main.py CLI integration (Task 7 — Phase 4 Observability)."""
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import main as main_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_STATE = {
    "messages": [],
    "query": "what is the weather?",
    "route": "research",
    "iterations": 0,
    "answer": "It is sunny.",
}


def _make_graph_mock(states=None):
    """Return a mock graph whose .stream() yields the given list of states."""
    if states is None:
        states = [_FAKE_STATE]
    graph_mock = MagicMock()
    graph_mock.stream.return_value = iter(states)
    return graph_mock


# ---------------------------------------------------------------------------
# Test A: --inspect mode calls inspect_run and exits
# ---------------------------------------------------------------------------


def test_main_inspect_mode_calls_inspect_run():
    mock_inspect = MagicMock()

    with patch("sys.argv", ["main.py", "--inspect", "abc123"]), \
         patch.object(main_mod, "inspect_run", mock_inspect), \
         patch.object(sys, "exit", side_effect=SystemExit(0)):
        try:
            main_mod.main()
        except SystemExit:
            pass

    mock_inspect.assert_called_once()
    first_arg = mock_inspect.call_args[0][0]
    assert first_arg == "abc123"


# ---------------------------------------------------------------------------
# Test B: normal query — tracer is initialised and start_run / finish_run called
# ---------------------------------------------------------------------------


def test_main_sets_tracer_and_starts_run():
    mock_tracer = MagicMock()
    mock_tracer_cls = MagicMock(return_value=mock_tracer)
    graph_mock = _make_graph_mock()

    # Do NOT patch set_tracer — let it run so get_tracer() returns mock_tracer
    with patch.object(main_mod, "Tracer", mock_tracer_cls), \
         patch.object(main_mod, "build_graph", return_value=graph_mock), \
         patch("builtins.print"):
        main_mod.run("what is the weather?")

    mock_tracer.start_run.assert_called_once()
    start_args = mock_tracer.start_run.call_args[0]
    assert len(start_args[0]) == 8            # short 8-char run ID
    assert start_args[1] == "what is the weather?"

    mock_tracer.finish_run.assert_called_once()
    finish_args = mock_tracer.finish_run.call_args[0]
    assert finish_args[0] == "It is sunny."   # answer extracted from final state
    assert isinstance(finish_args[1], int)    # duration_ms is an integer


# ---------------------------------------------------------------------------
# Test C: run_id is printed to stdout
# ---------------------------------------------------------------------------


def test_main_prints_run_id():
    mock_tracer = MagicMock()
    mock_tracer_cls = MagicMock(return_value=mock_tracer)
    graph_mock = _make_graph_mock()

    captured = StringIO()

    with patch.object(main_mod, "Tracer", mock_tracer_cls), \
         patch.object(main_mod, "set_tracer"), \
         patch.object(main_mod, "build_graph", return_value=graph_mock), \
         patch("sys.stdout", captured):
        main_mod.run("test query")

    output = captured.getvalue()
    assert "Run ID:" in output


# ---------------------------------------------------------------------------
# Test D: no query and no --inspect prints help and exits 1
# ---------------------------------------------------------------------------


def test_main_no_args_exits_1():
    with patch("sys.argv", ["main.py"]):
        try:
            main_mod.main()
            exited = False
            exit_code = None
        except SystemExit as exc:
            exited = True
            exit_code = exc.code

    assert exited, "Expected SystemExit when no args provided"
    assert exit_code == 1
