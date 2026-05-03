# Erid

A personal research and decision assistant that knows you.

Named after the home planet of Rocky in *Project Hail Mary* by Andy Weir. Rocky is an Eridian — a completely alien intelligence with his own hard-earned knowledge and perspective — who becomes your most trusted thinking partner precisely because of how specific and non-generic his context is. The whole story is about two intelligences combining their different knowledge bases to solve something neither could alone.

That's what this is. Not a generic assistant that knows everything about the world but nothing about you. A personal intelligence layer that starts from *your* context — your decisions, your lessons, your codebases, your preferences — and compounds that over time into better research and better decisions.

Also: everyone on Erid is very, very kind and brave.

---

## What it does

- **Research** — searches the web for current information, synthesizes into a cited answer
- **Knowledge base queries** — reads your personal markdown KB (decisions, lessons, preferences, project notes)
- **Codebase exploration** — navigates and answers questions about your historical projects
- **Decision support** — researches decisions grounded in your own past choices and preferences, not just generic best practices
- **Clarifying questions** — asks for clarification on ambiguous queries before starting research (max 2 rounds)

## Personal knowledge base

Erid reads markdown files you maintain:

```
knowledge-base/
├── decisions/     # architectural decisions + rationale
├── lessons/       # lessons learned from projects
├── preferences/   # personal tech opinions and style
└── projects/      # notes on historical codebases
```

The more you feed it, the more it sounds like you.

## Setup

```bash
cp .env.example .env
# Add ANTHROPIC_API_KEY and TAVILY_API_KEY

# Create a virtual environment
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

After the one-time setup, just activate before running:

```bash
source .venv/bin/activate
```

## Usage

```bash
python main.py "What is LangGraph and how does it work?"
python main.py "How does auth work in my chefs-hub project?"
python main.py "Should I use FastAPI or Django for this service?"
```

### Inspect past runs

Every run is traced to `~/.erid/traces.db`. Use `--inspect` to replay any run:

```bash
python main.py --inspect last          # most recent run
python main.py --inspect <run-id>      # specific run by ID
```

Output shows a full timeline: nodes, tool calls, token counts, cost, and the final answer.

## Phases

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | ReAct loop + streaming | ✓ Complete |
| 2 | Tools, orchestration, personal KB | ✓ Complete |
| 3 | Human-in-the-loop | ✓ Complete |
| 4 | Observability | ✓ Complete |
| 5 | Evals | Planned |
| 6 | Semantic memory (RAG) | Planned |

See [`docs/superpowers/roadmap.md`](docs/superpowers/roadmap.md) for the full plan.
