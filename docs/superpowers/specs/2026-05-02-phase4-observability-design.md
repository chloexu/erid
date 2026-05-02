# Phase 4 — Observability Design

**Date:** 2026-05-02
**Status:** Approved

---

## Overview

Every Erid run writes a structured trace to a local SQLite database. A `--inspect` CLI flag replays any past run as a timeline + summary. Cost is computed per run from token counts × model pricing.

---

## Storage

**Location:** `~/.erid/traces.db` — user-level, persists across clones, never accidentally committed.

**Two tables:**

### `runs`
| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT PK | UUID4 |
| `timestamp` | TEXT | ISO8601 |
| `query` | TEXT | original query (post-clarification if edited) |
| `route` | TEXT | `research \| codebase \| knowledge_base \| decide` |
| `total_input_tokens` | INTEGER | sum across all LLM calls |
| `total_output_tokens` | INTEGER | sum across all LLM calls |
| `total_cost_usd` | REAL | computed at finish |
| `duration_ms` | INTEGER | wall clock from start to finish |
| `final_answer` | TEXT | full answer text |

### `events`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | autoincrement |
| `run_id` | TEXT FK | references `runs.id` |
| `seq` | INTEGER | ordering within run |
| `event_type` | TEXT | `node_start \| node_end \| tool_call \| clarification \| routing` |
| `name` | TEXT | node label or tool name |
| `timestamp` | TEXT | ISO8601 |
| `duration_ms` | INTEGER | null for `node_start`, `clarification`, `routing` |
| `input_tokens` | INTEGER | null except `node_end` |
| `output_tokens` | INTEGER | null except `node_end` |
| `cost_usd` | REAL | null except `node_end` |
| `detail` | TEXT | JSON blob — tool input, routing reasoning, clarification Q&A |

---

## Cost Pricing Constants

Hardcoded at definition time, updated manually when Anthropic changes pricing:

| Model | Input ($/MTok) | Output ($/MTok) |
|-------|---------------|----------------|
| claude-sonnet-4-6 | $3.00 | $15.00 |
| claude-haiku-4-5-20251001 | $0.80 | $4.00 |

Cost per LLM call = `(input_tokens / 1_000_000 * input_rate) + (output_tokens / 1_000_000 * output_rate)`

---

## Module Structure

New `observability/` package:

```
observability/
├── __init__.py        # exports: tracer (NullTracer default), set_tracer()
├── tracer.py          # Tracer + NullTracer classes, SQLite persistence
└── inspect.py         # --inspect display logic
```

---

## Tracer API

```python
tracer.start_run(run_id: str, query: str) -> None
tracer.record_clarification(question: str, answer: str) -> None
tracer.record_routing(route: str, reasoning: str) -> None
tracer.record_node_start(label: str) -> None
tracer.record_llm_call(label: str, model: str, input_tok: int, output_tok: int, duration_ms: int) -> None
tracer.record_tool_call(name: str, input: dict, duration_ms: int, denied: bool = False) -> None
tracer.finish_run(answer: str, duration_ms: int) -> None
```

`observability/__init__.py` exports a module-level `tracer` instance set to `NullTracer()` by default. All methods on `NullTracer` are no-ops. `main.py` calls `set_tracer(Tracer())` at startup, replacing the no-op.

This means existing agent code importing `from observability import tracer` never breaks in tests or other contexts where tracing isn't initialized.

---

## Instrumentation Points

### `main.py`
- Before graph run: `tracer.start_run(run_id, query)`
- After graph run: `tracer.finish_run(answer, duration_ms)`
- Print `Run ID: <id>` at end of every normal run

### `agents/streaming.py` — `stream_agent_turn`
- Add optional `tracer` param (defaults to `NullTracer`)
- Wrap the stream call with `time.monotonic()`
- After `get_final_message()`: `tracer.record_llm_call(label, model, usage.input_tokens, usage.output_tokens, duration_ms)`

### `agents/supervisor.py`
- After each clarification round: `tracer.record_clarification(question, answer)`
- After routing: `tracer.record_routing(route, reasoning_line)`

### `agents/researcher.py` + `agents/decision.py` — tool nodes
- Wrap `_dispatch` with `time.monotonic()`
- After dispatch: `tracer.record_tool_call(name, inputs, duration_ms, denied)`

### Agent nodes (`researcher_agent_node`, `decision_agent_node`, etc.)
- Before calling `stream_agent_turn`: `tracer.record_node_start(label)`
- Pass `tracer` into `stream_agent_turn`

---

## CLI Interface

```bash
python main.py "query"              # normal run — prints Run ID at end
python main.py --inspect <run-id>   # inspect a specific run
python main.py --inspect last       # inspect most recent run
```

`--inspect` and normal query mode are mutually exclusive. `--inspect` does not invoke the graph.

---

## `--inspect` Output Format

```
Run: a1b2c3  |  2026-05-02 14:32:01  |  route: codebase  |  8.3s  |  $0.023

Timeline:
  +0.000s  [supervisor] start
  +0.341s  [supervisor] clarification: "Which project?" → "chefs-hub"
  +1.102s  [supervisor] route: codebase  (0.8s, 234 in / 45 out)
  +1.103s  [researcher] start
  +2.891s    tool: list_directory  "."  (0.12s)
  +3.014s    tool: read_file  "src/auth.py"  (0.08s)  [denied]
  +5.231s  [researcher] done  (3.2s, 1842 in / 312 out, $0.018)
  +5.232s  [summarizer] start
  +8.102s  [summarizer] done  (2.9s, 2104 in / 489 out, $0.005)

Summary:
  Route:   codebase
  Tokens:  4,180 in / 846 out
  Cost:    $0.023
  Answer:  Auth in chefs-hub uses JWT tokens...
```

- Tool calls are indented under their parent node
- Denied tool calls show `[denied]`
- Answer is truncated to ~100 chars in summary; full answer is in the DB

---

## Error Handling

- If `~/.erid/` doesn't exist, create it on first run
- If the DB write fails, log a warning to stderr but do not crash the run — tracing is best-effort
- `--inspect` on unknown run ID prints: `No run found with ID: <id>`

---

## Out of Scope (Phase 4)

- `--cost` summary across multiple runs (Phase 5 can use the DB directly)
- Streaming/live trace output
- Remote trace storage
- Cache token tracking (Anthropic prompt caching)
