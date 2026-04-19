# chefs-hub / chefs-hub-service

**Stack:** NestJS (service), React (frontend)
**Status:** Personal project, intermittently maintained

## What it is
A recipe and meal-planning app. Backend handles recipes, ingredients, and weekly meal plans. Frontend is a React SPA.

## Architecture decisions
- NestJS chosen to learn its DI system — would choose FastAPI today
- No auth initially, JWT added later — caused a painful refactor
- Postgres with TypeORM — migrations have been reliable

## Known pain points
- TypeORM migrations require careful ordering; ran into circular dependency issues
- No test coverage on the service layer — tech debt

## Codebase location
`/Users/chloexu/Chloe/code/chefs-hub` (frontend)
`/Users/chloexu/Chloe/code/chefs-hub-service` (backend)
