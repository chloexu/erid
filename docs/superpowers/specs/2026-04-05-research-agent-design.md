# Research Agent — Design Spec

**Date:** 2026-04-05
**Status:** Approved
**Goal:** Build a lightweight research agent in Python using LangGraph + Claude API, incrementally learning the core components of an agentic system.

---

## Overview

`research-agent` is a Python CLI application that answers natural language research questions. It is built in three phases, each teaching a distinct agentic concept:

| Phase | Concept | What gets added |
|-------|---------|-----------------|
| 1 | The Loop | ReAct pattern, state, graph wiring |
| 2 | Tools + Orchestration | More tools, supervisor, subagents |
| 3 | Memory | Persistent conversation history via SQLite |

---

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** LangGraph
- **LLM:** Claude API (claude-sonnet-4-6)
- **Search tool:** Tavily API (free tier)
- **Memory backend:** SQLite via LangGraph's `SqliteSaver`
- **Interface:** CLI (stdin/stdout)

---

## Phase 1 — The Loop

### Goal
Understand how an agent decides, acts, observes, and repeats.

### Architecture

```
User query
    │
    ▼
┌─────────────┐
│ Agent Node  │◄──────────────────┐
│ (Claude)    │                   │
└──────┬──────┘                   │
       │ tool_call or FINISH       │
       ▼                          │
┌─────────────┐                   │
│  Tool Node  │───── result ──────┘
│ (executor)  │
└─────────────┘
```

The graph loops between the Agent Node and Tool Node until the agent emits a final answer (no tool call).

### Components

- **`state.py`** — Typed dict with fields: `messages` (list), `query` (str), `iterations` (int)
- **`graph.py`** — `StateGraph` with two nodes (`agent`, `tools`) and a conditional edge: if the agent response contains a tool call, route to `tools`; otherwise end
- **`tools/search.py`** — Wraps Tavily search API, returns top 3 results as text
- **`main.py`** — CLI entrypoint: reads query from stdin, runs graph, prints final answer

### Iteration guard
Max 10 iterations to prevent infinite loops. If exceeded, the agent returns whatever it has.

---

## Phase 2 — Tools + Orchestration

### Goal
Understand tool diversity and how a supervisor routes work between specialized subagents.

### New tools

- **`tools/calculator.py`** — Evaluates simple math expressions safely (no `eval` on arbitrary input; uses `numexpr` or restricted AST parsing)
- **`tools/file_reader.py`** — Reads a local file by path, returns contents as string (capped at 10KB)

### Supervisor pattern

A `supervisor` node is added to the graph. It inspects the query and routes to one of two subgraphs:

- **`agents/researcher.py`** — Fetches and aggregates information using `web_search` and `file_reader`
- **`agents/summarizer.py`** — Takes researcher output and produces a cited, concise answer

Routing logic: the supervisor uses a simple classifier prompt to decide which subagent(s) to invoke and in what order. Output of researcher is passed as input to summarizer.

```
User query
    │
    ▼
┌──────────────┐
│  Supervisor  │
└──────┬───────┘
       │
   ┌───┴────────────┐
   ▼                ▼
Researcher      (passthrough
Subgraph         if summary
   │             not needed)
   │
   ▼
Summarizer
Subgraph
   │
   ▼
Final answer
```

---

## Phase 3 — Memory

### Goal
Understand how agents persist and retrieve context across sessions.

### Implementation

- Uses LangGraph's built-in `SqliteSaver` checkpointer
- Conversation history stored in `memory/agent.db`
- Each CLI session uses a `thread_id` (default: `"default"`, overridable via `--thread` flag)
- On each new query, prior messages for that thread are loaded and prepended to context

### Memory boundaries
- Per-thread history only (no cross-thread retrieval)
- No vector search in this phase — simple chronological message history
- History capped at last 20 messages to avoid context overflow

---

## Project Structure

```
research-agent/
├── main.py                  # CLI entrypoint
├── graph.py                 # LangGraph StateGraph definition
├── state.py                 # Shared AgentState TypedDict
├── agents/
│   ├── researcher.py        # Researcher subagent subgraph
│   └── summarizer.py        # Summarizer subagent subgraph
├── tools/
│   ├── search.py            # Tavily web search tool
│   ├── calculator.py        # Safe math expression evaluator
│   └── file_reader.py       # Local file reader tool
├── memory/
│   └── store.py             # SqliteSaver setup and thread management
├── docs/
│   └── superpowers/specs/
│       └── 2026-04-05-research-agent-design.md
├── .env.example             # ANTHROPIC_API_KEY, TAVILY_API_KEY
└── requirements.txt
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| LangGraph over raw API | Transparent graph model maps directly to loop/orchestration concepts |
| Claude API directly | No LangChain wrapper — keeps tool binding and message handling visible |
| SQLite for memory | Zero infrastructure, inspectable with any SQLite viewer |
| Phased build | Each phase is independently runnable; later phases extend, don't rewrite |
| No RAG in Phase 3 | Keeps memory simple; vector store is a natural Phase 4 extension |

---

## Success Criteria

- Phase 1: Agent can answer a research question using web search, looping until it has enough info
- Phase 2: Supervisor correctly routes queries; researcher and summarizer produce cited output
- Phase 3: Agent recalls context from previous queries in the same thread

---

## Out of Scope (for now)

- Vector store / semantic memory retrieval
- Streaming output
- Web UI
- Authentication or multi-user support
