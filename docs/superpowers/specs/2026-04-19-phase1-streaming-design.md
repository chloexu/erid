# Phase 1 Streaming & Verbose Output — Design

**Date:** 2026-04-19
**Scope:** research-agent Phase 1 only — no new tools, no new nodes

## Goal

Make every step of the ReAct loop visible in real time so agent behavior can be evaluated and understood during learning.

## UX: Verbose Mode (Option B)

Every agent invocation and tool call is printed to stdout as it happens:

```
Query: What is LangGraph?

Thinking...
LangGraph is... [reasoning tokens stream live]

[tool_use] search
  input: {"query": "LangGraph framework"}

[tool_result] search
  LangGraph is a library for building stateful, multi-actor...
  [full raw Tavily result]

Thinking...
Based on the search results... [final answer streams live]
```

- Reasoning tokens from every LLM call stream word-by-word
- Tool name + full input printed when tool fires
- Full raw tool result printed (not truncated)
- "Thinking..." printed at the start of each agent node invocation

## Implementation: Option 2 (graph.stream + Anthropic streaming)

### `graph.py` — `agent_node`

Switch from `client.messages.create()` to `client.messages.stream()` context manager.

During streaming:
- Print `Thinking...` once at entry
- For each text delta, print the token immediately (no newline) and accumulate it
- For `tool_use` blocks, accumulate id/name/input as they arrive
- After stream closes, assemble the same content list shape as before and return it

The return value shape is unchanged — `{"messages": [...], "iterations": n}` — so routing logic and tool_node are unaffected.

### `main.py`

Switch from `graph.invoke()` to `graph.stream()` with `stream_mode="updates"`.

For each event yielded:
- If it's a `tools` node update: iterate the last message's tool_results and print tool name + input + full result content
- Agent node output is already printed live inside `agent_node` itself

Remove the final `print(answer)` block — the answer has already streamed to stdout.

### What does NOT change

- `state.py` — AgentState shape unchanged
- `tool_node` — logic unchanged
- `dispatch_tool` — unchanged
- `should_continue` — routing unchanged
- Tests — no behavior change, tests still pass

## Key Implementation Detail

`client.messages.stream()` is a context manager. Text deltas arrive via `on_text` or by iterating the stream. Tool use blocks arrive as `content_block_start` / `content_block_delta` events. Accumulate them, then after `__exit__` assemble the final content list to return to LangGraph state.

Use `print(token, end="", flush=True)` for live token output without buffering.

## Out of Scope

- Interactive follow-up questions (Phase 2+)
- Log levels or `--verbose` flag
- Structured logging / JSON output
- Any new tools or agent nodes
