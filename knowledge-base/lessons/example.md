# Lessons Learned: Microservices Too Early

**Date:** 2025-11-01

## What happened
Split a monolith into microservices before traffic justified it. Spent 3 weeks on service discovery, shared auth, and distributed tracing before writing any product features.

## Lesson
Start as a monolith. Extract services only when a specific bottleneck demands it — not for architectural purity. The inflection point is usually ~10k RPS or team size >8.

## Applied in
chefs-hub-service: kept as monolith, added feature flags for gradual rollout.
