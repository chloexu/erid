# Erid — Roadmap

Each phase has its own design spec and implementation plan written when that phase is ready to build.

---

## Phase 1 — The Loop ✓

A ReAct loop: LangGraph StateGraph, Anthropic SDK direct, Tavily web search, 10-iteration guard, verbose streaming output.

- Spec: `specs/2026-04-05-research-agent-design.md`
- Streaming spec: `specs/2026-04-19-phase1-streaming-design.md`
- Plan: `plans/2026-04-05-research-agent-phase1.md`

---

## Phase 2 — Tools, Orchestration & Agent Identity ✓

Personal research + decision assistant. Supervisor routes to four paths: web research, codebase exploration, knowledge base queries, and decision support. Personal knowledge base (markdown). Streaming extended to all LLM calls.

- Spec: `specs/2026-04-19-phase2-redesign.md`
- Plan: `plans/2026-04-19-erid-phase2.md`

---

## Phase 3 — Human-in-the-loop ✓

Supervisor pauses on ambiguous queries and asks the user to clarify before routing. Enriched query (original + clarifying Q&A) is passed to all downstream agents. Max 2 clarification rounds before proceeding. Uses Haiku for the lightweight clarity check, Sonnet for classification. Decision framing confirmation (Haiku extracts framing, user confirms/corrects before research). File access boundaries: blocks absolute paths and path traversal; KB route restricted to `knowledge-base/`.

Teaches: when to interrupt vs. proceed, structured human-in-the-loop without a checkpointer, cheap pre-flight LLM calls.

---

## Phase 4 — Observability ✓

Every run writes a structured trace to SQLite (`~/.erid/traces.db`): token counts, tool calls, latency per node, routing decisions, cost per call, final answer. `--inspect <run-id>` (or `--inspect last`) CLI replays any past run as a timeline + summary. Summarizer uses Haiku (~4x cheaper than Sonnet) since synthesis is a writing task, not a reasoning task.

Teaches: production debuggability, cost tracking, model cost optimization.

Provides real run data for Phase 5 evals.

- Spec: `specs/2026-05-02-phase4-observability-design.md`
- Plan: `plans/2026-05-02-erid-phase4.md`

---

## Phase 5 — Evals

Eval harness against golden Q&A pairs sourced from Phase 4 traces. Claude-as-judge scores response quality. Baseline the agent across all prior phases. Teaches: the eval loop, LLM-as-judge pattern, how to measure improvement.

Baseline used to measure Phase 6 RAG improvement.

- Spec: *to be written*
- Plan: *to be written*

---

## Phase 6 — Semantic Memory (RAG)

Replace KB file reading with vector retrieval (Chroma or in-memory). Embed KB entries at load time. Retrieve semantically relevant past context rather than reading all files. Teaches: embeddings, retrieval, semantic vs. verbatim memory.

Payoff: re-run Phase 5 evals to measure before/after improvement from RAG.

- Spec: *to be written*
- Plan: *to be written*

