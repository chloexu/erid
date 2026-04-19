# Erid — Phase 2 Design: Tools, Orchestration & Agent Identity

**Date:** 2026-04-19
**Scope:** Phase 2 full redesign

## Agent Identity

A **personal research + decision assistant that knows you** — combines live web knowledge with a personal knowledge base (markdown files you curate, enriched by conversations over time). Differentiated from Claude/ChatGPT by having access to your own accumulated context: past architectural decisions, lessons learned, personal tech preferences, historical codebases.

**Primary use cases:**

- **Codebase research**: Navigate and answer questions about historical codebases ("how does auth work in project X?")
- **Decision support**: Research a decision using both web sources and your personal KB, output structured pro/con grounded in your own preferences and history

## Phase 2 Scope

### Tools (revised)


| Tool              | Status                        | Purpose                                          |
| ----------------- | ----------------------------- | ------------------------------------------------ |
| `search` (Tavily) | Keep                          | Web research for both use cases                  |
| `read_file`       | Keep                          | Reads KB markdown files + codebase files         |
| `list_directory`  | **New** (replaces calculator) | Navigate codebase structure before reading files |
| `calculator`      | **Dropped**                   | No real use case for the agent's purpose         |


### Supervisor Routing

Supervisor classifies query into one of three routes with a brief reasoning line before outputting the route (teaches structured output prompting):

- `**research`** → researcher loop (web search + KB read → summarizer)
- `**codebase**` → codebase explorer (directory list + file read → summarizer)
- `**decide**` → decision node (web research + personal KB read → structured pro/con output)

The `decide` route is the key differentiator: it reads your personal KB first, uses those preferences as priors, then supplements with web research. Output is a structured pro/con with explicit citations to both web sources and your own past decisions.

### Streaming (extended from Phase 1)

Phase 1 streaming carries forward to all LLM calls in Phase 2:

- Supervisor node streams its reasoning before outputting the route
- Researcher node streams per-token (already designed in Phase 1)
- Summarizer/decision node streams the final answer

Every LLM call in the graph uses `client.messages.stream()`. This makes the full orchestration visible — you see the supervisor think, route, and then watch the appropriate subgraph execute.

### Supervisor Output Format

Supervisor outputs two lines before the single-word route, teaching you how to prompt for structured reasoning:

```
Reasoning: This is a comparison between two frameworks, requiring web research
and checking past decisions.
Route: decide
```

Parser extracts the last word of `Route:` line as the routing key.

### Personal Knowledge Base Structure

Seeded via markdown files the user maintains:

```
knowledge-base/
├── decisions/       # past architectural decisions + rationale
├── lessons/         # lessons learned from projects
├── preferences/     # personal tech opinions, style preferences
└── projects/        # notes on historical codebases
```

Agent reads these files as context. Writing to the KB (conversational enrichment) is deferred to Phase 3 (Human-in-the-loop — user approves before anything is written).

### Files Changed


| File                      | Change                                                                 |
| ------------------------- | ---------------------------------------------------------------------- |
| `tools/calculator.py`     | Deleted                                                                |
| `tools/file_reader.py`    | Keep as-is                                                             |
| `tools/list_directory.py` | New                                                                    |
| `agents/researcher.py`    | Add streaming, add `read_file` + `list_directory` to tool set          |
| `agents/summarizer.py`    | Add streaming                                                          |
| `agents/decision.py`      | New — decision support node                                            |
| `graph.py`                | Supervisor with reasoning output, three routes, decision node wired in |
| `state.py`                | Add `route` field with three values                                    |
| `main.py`                 | Extend streaming display for supervisor reasoning + route announcement |


