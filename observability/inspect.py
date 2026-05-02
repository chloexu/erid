import json
import sqlite3
from datetime import datetime
from pathlib import Path


def _parse_ts(ts: str) -> float:
    """Returns milliseconds since epoch for offset calculations."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt.timestamp() * 1000


def inspect_run(run_id: str, db_path: Path) -> None:
    if not db_path.exists():
        print(f"No run found with ID: {run_id}")
        return

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        if run_id == "last":
            run = conn.execute(
                "SELECT * FROM runs ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
        else:
            run = conn.execute(
                "SELECT * FROM runs WHERE id = ?", (run_id,)
            ).fetchone()

        if not run:
            print(f"No run found with ID: {run_id}")
            return

        events = conn.execute(
            "SELECT * FROM events WHERE run_id = ? ORDER BY seq",
            (run["id"],),
        ).fetchall()

    duration_s = run["duration_ms"] / 1000 if run["duration_ms"] else 0
    cost_str = f"${run['total_cost_usd']:.3f}" if run["total_cost_usd"] is not None else "?"
    ts_display = run["timestamp"][:19].replace("T", " ") if run["timestamp"] else "?"

    print(
        f"\nRun: {run['id']}  |  {ts_display}  |  "
        f"route: {run['route'] or '?'}  |  {duration_s:.1f}s  |  {cost_str}"
    )

    run_start_ms = _parse_ts(run["timestamp"]) if run["timestamp"] else 0

    print("\nTimeline:")
    for event in events:
        offset_s = (_parse_ts(event["timestamp"]) - run_start_ms) / 1000
        prefix = f"  +{offset_s:.3f}s"
        etype = event["event_type"]
        name = event["name"]

        if etype == "node_start":
            print(f"{prefix}  [{name}] start")

        elif etype == "node_end":
            dur = f"{event['duration_ms'] / 1000:.1f}s" if event["duration_ms"] is not None else "?"
            tok = (
                f"{event['input_tokens']:,} in / {event['output_tokens']:,} out"
                if event["input_tokens"] is not None
                else ""
            )
            cost_part = f", ${event['cost_usd']:.3f}" if event["cost_usd"] is not None else ""
            print(f"{prefix}  [{name}] done  ({dur}, {tok}{cost_part})")

        elif etype == "tool_call":
            detail = json.loads(event["detail"]) if event["detail"] else {}
            inp = detail.get("input", {})
            path_or_query = inp.get("path") or inp.get("query", "")
            dur = f"{event['duration_ms'] / 1000:.2f}s" if event["duration_ms"] is not None else "?"
            denied_str = "  [denied]" if detail.get("denied") else ""
            print(f'{prefix}    tool: {name}  "{path_or_query}"  ({dur}){denied_str}')

        elif etype == "clarification":
            detail = json.loads(event["detail"]) if event["detail"] else {}
            q = detail.get("question", "")
            a = detail.get("answer", "")
            print(f'{prefix}  [supervisor] clarification: "{q}" → "{a}"')

        elif etype == "routing":
            detail = json.loads(event["detail"]) if event["detail"] else {}
            print(f"{prefix}  [supervisor] route: {detail.get('route', '')}")

    print("\nSummary:")
    print(f"  Route:   {run['route'] or '?'}")
    if run["total_input_tokens"] is not None:
        print(f"  Tokens:  {run['total_input_tokens']:,} in / {run['total_output_tokens']:,} out")
    if run["total_cost_usd"] is not None:
        print(f"  Cost:    ${run['total_cost_usd']:.3f}")
    answer = run["final_answer"] or ""
    truncated = answer[:100] + ("..." if len(answer) > 100 else "")
    print(f"  Answer:  {truncated}")
