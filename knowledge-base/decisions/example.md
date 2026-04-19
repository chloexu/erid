# FastAPI over Flask for new REST APIs

**Date:** 2026-01-15
**Status:** Active

## Decision
Use FastAPI for all new REST API services.

## Rationale
- Async-native fits I/O-heavy workloads
- Auto-generated OpenAPI docs save integration time
- Type hints + Pydantic catch bugs at the boundary
- Performance benchmarks show 2-3x throughput vs Flask for concurrent requests

## Trade-offs accepted
- Smaller ecosystem than Flask/Django
- Less opinionated — more setup for auth, admin, etc.

## When to revisit
If the project needs a full-stack framework with ORM, auth, and admin out of the box — consider Django.
