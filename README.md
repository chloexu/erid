# Erid

A personal research and decision assistant that knows you.

Named after the home planet of Rocky in *Project Hail Mary* by Andy Weir. Rocky is an Eridian — a completely alien intelligence with his own hard-earned knowledge and perspective — who becomes your most trusted thinking partner precisely because of how specific and non-generic his context is. The whole story is about two intelligences combining their different knowledge bases to solve something neither could alone.

That's what this is. Not a generic assistant that knows everything about the world but nothing about you. A personal intelligence layer that starts from *your* context — your decisions, your lessons, your codebases, your preferences — and compounds that over time into better research and better decisions.

Also: everyone on Erid is very, very kind and brave.

---

## What it does

- **Research** — searches the web and your personal knowledge base, synthesizes across both
- **Codebase exploration** — navigates and answers questions about your historical projects
- **Decision support** — researches decisions grounded in your own past choices and preferences, not just generic best practices

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

# Create a virtual environment (ARM64 on Apple Silicon)
arch -arm64 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m venv .venv
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

### Output modes

By default, output uses simple labels:

```
Thinking...
[tool_use] search
[tool_result] search
  <raw Tavily response>
Thinking...
<final answer streams here>
```

Add `--verbose` (or `-v`) to see granular labels that show exactly what each line is and where it comes from:

```
[agent: loop 1/10] deciding next action...   ← local loop, LLM about to stream
<raw LLM tokens>                             ← Anthropic stream, unprocessed
[tool_call → search]                         ← LLM decided to call a tool
  input: {'query': '...'}
[tool_result ← search] raw response:         ← raw Tavily API response, no processing
  <result>
[agent: loop 2/10] deciding next action...
<final answer streams here>
```

```bash
python main.py "What is LangGraph?" --verbose
python main.py "What is LangGraph?" -v
```

## Phases

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | ReAct loop + streaming | ✓ Complete |
| 2 | Tools, orchestration, personal KB | In design |
| 3 | Human-in-the-loop | Planned |
| 4 | Observability | Planned |
| 5 | Evals | Planned |
| 6 | Semantic memory (RAG) | Planned |

See [`docs/superpowers/roadmap.md`](docs/superpowers/roadmap.md) for the full plan.
