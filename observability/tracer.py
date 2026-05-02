import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path.home() / ".erid" / "traces.db"

PRICING = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    timestamp TEXT,
    query TEXT,
    route TEXT,
    total_input_tokens INTEGER,
    total_output_tokens INTEGER,
    total_cost_usd REAL,
    duration_ms INTEGER,
    final_answer TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT REFERENCES runs(id),
    seq INTEGER,
    event_type TEXT,
    name TEXT,
    timestamp TEXT,
    duration_ms INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL,
    detail TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _compute_cost(model: str, input_tok: int, output_tok: int) -> float:
    rates = PRICING.get(model, PRICING["claude-sonnet-4-6"])
    return (input_tok / 1_000_000 * rates["input"]) + (output_tok / 1_000_000 * rates["output"])


class NullTracer:
    def start_run(self, run_id: str, query: str) -> None: pass
    def record_clarification(self, question: str, answer: str) -> None: pass
    def record_routing(self, route: str, reasoning: str) -> None: pass
    def record_node_start(self, label: str) -> None: pass
    def record_llm_call(self, label: str, model: str, input_tok: int, output_tok: int, duration_ms: int) -> None: pass
    def record_tool_call(self, name: str, tool_input: dict, duration_ms: int, denied: bool = False) -> None: pass
    def finish_run(self, answer: str, duration_ms: int) -> None: pass


class Tracer:
    def __init__(self, db_path: Path = DB_PATH):
        self._db_path = db_path
        self._run_id: Optional[str] = None
        self._seq = 0
        self._total_input = 0
        self._total_output = 0
        self._total_cost = 0.0
        self._current_route = ""
        self._init_db()

    def _init_db(self) -> None:
        """Initialise the SQLite database. Raises on failure (e.g. permission error).
        This is intentional: if the DB cannot be created at startup, the caller
        should handle it. Unlike write methods, DB init failure is not best-effort."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_SCHEMA)

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _insert_event(
        self,
        event_type: str,
        name: str,
        duration_ms: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        cost_usd: Optional[float] = None,
        detail: Optional[dict] = None,
    ) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """INSERT INTO events
                       (run_id, seq, event_type, name, timestamp, duration_ms,
                        input_tokens, output_tokens, cost_usd, detail)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        self._run_id,
                        self._next_seq(),
                        event_type,
                        name,
                        _now(),
                        duration_ms,
                        input_tokens,
                        output_tokens,
                        cost_usd,
                        json.dumps(detail) if detail is not None else None,
                    ),
                )
        except Exception as e:
            print(f"[tracer] warning: {e}", file=sys.stderr)

    def start_run(self, run_id: str, query: str) -> None:
        self._run_id = run_id
        self._seq = 0
        self._total_input = 0
        self._total_output = 0
        self._total_cost = 0.0
        self._current_route = ""
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT INTO runs (id, timestamp, query) VALUES (?, ?, ?)",
                    (run_id, _now(), query),
                )
        except Exception as e:
            print(f"[tracer] warning: {e}", file=sys.stderr)

    def record_clarification(self, question: str, answer: str) -> None:
        self._insert_event(
            "clarification", "supervisor",
            detail={"question": question, "answer": answer},
        )

    def record_routing(self, route: str, reasoning: str) -> None:
        self._current_route = route
        self._insert_event(
            "routing", "supervisor",
            detail={"route": route, "reasoning": reasoning},
        )

    def record_node_start(self, label: str) -> None:
        self._insert_event("node_start", label)

    def record_llm_call(
        self,
        label: str,
        model: str,
        input_tok: int,
        output_tok: int,
        duration_ms: int,
    ) -> None:
        cost = _compute_cost(model, input_tok, output_tok)
        self._total_input += input_tok
        self._total_output += output_tok
        self._total_cost += cost
        self._insert_event(
            "node_end", label,
            duration_ms=duration_ms,
            input_tokens=input_tok,
            output_tokens=output_tok,
            cost_usd=cost,
        )

    def record_tool_call(
        self, name: str, tool_input: dict, duration_ms: int, denied: bool = False
    ) -> None:
        self._insert_event(
            "tool_call", name,
            duration_ms=duration_ms,
            detail={"input": tool_input, "denied": denied},
        )

    def finish_run(self, answer: str, duration_ms: int) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """UPDATE runs
                       SET route=?, total_input_tokens=?, total_output_tokens=?,
                           total_cost_usd=?, duration_ms=?, final_answer=?
                       WHERE id=?""",
                    (
                        self._current_route,
                        self._total_input,
                        self._total_output,
                        self._total_cost,
                        duration_ms,
                        answer,
                        self._run_id,
                    ),
                )
        except Exception as e:
            print(f"[tracer] warning: {e}", file=sys.stderr)
