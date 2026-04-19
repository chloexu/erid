# Research Agent — Roadmap

Each phase has its own design spec and implementation plan written when that phase is ready to build.

---

## Phase 1 — The Loop ✓
A ReAct loop: LangGraph StateGraph, Anthropic SDK direct, Tavily web search, 10-iteration guard, verbose streaming output.

- Spec: `specs/2026-04-05-research-agent-design.md`
- Streaming spec: `specs/2026-04-19-phase1-streaming-design.md`
- Plan: `plans/2026-04-05-research-agent-phase1.md`

---

## Phase 2 — Tools, Orchestration & Agent Identity
Personal research + decision assistant. Supervisor routes to three paths: web research, codebase exploration, decision support. Personal knowledge base (markdown). Streaming extended to all LLM calls.

- Spec: `specs/2026-04-19-phase2-redesign.md`
- Plan: _to be written after spec review_

---

## Phase 3 — Human-in-the-loop
Agent pauses before writing to the knowledge base and asks for approval. User can approve, edit, or abort. Teaches: LangGraph interrupt patterns, building collaborative rather than fully autonomous agents.

Natural trigger: KB write from Phase 2's conversational enrichment needs approval before persisting.

- Spec: _to be written_
- Plan: _to be written_

---

## Phase 4 — Observability
Every run writes a structured JSON trace: token counts, tool calls, latency per node, routing decisions, final answer. `--inspect <run-id>` CLI to replay any past run. Teaches: production debuggability, cost tracking.

Provides real run data for Phase 5 evals.

- Spec: _to be written_
- Plan: _to be written_

---

## Phase 5 — Evals
Eval harness against golden Q&A pairs sourced from Phase 4 traces. Claude-as-judge scores response quality. Baseline the agent across all prior phases. Teaches: the eval loop, LLM-as-judge pattern, how to measure improvement.

Baseline used to measure Phase 6 RAG improvement.

- Spec: _to be written_
- Plan: _to be written_

---

## Phase 6 — Semantic Memory (RAG)
Replace KB file reading with vector retrieval (Chroma or in-memory). Embed KB entries at load time. Retrieve semantically relevant past context rather than reading all files. Teaches: embeddings, retrieval, semantic vs. verbatim memory.

Payoff: re-run Phase 5 evals to measure before/after improvement from RAG.

- Spec: _to be written_
- Plan: _to be written_
