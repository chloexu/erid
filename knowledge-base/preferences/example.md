# Tech Preferences

## Languages
- **Primary:** TypeScript (frontend), Python (agents/ML), Go (high-throughput services)
- **Avoid:** PHP, Ruby (no existing context, not worth context-switching)

## Databases
- PostgreSQL for relational workloads — familiar, battle-tested, Fly.io support
- SQLite for local-only tools and prototypes
- Avoid NoSQL unless the data model is genuinely document-shaped

## Deployment
- Fly.io for personal projects — simple, affordable, good DX
- AWS for anything needing scale or enterprise compliance
- Docker always — no bare-metal deploys

## Frontend
- React + TypeScript for web, Expo for mobile
- Avoid class components, prefer hooks
- Tailwind for styling — utility-first keeps it fast
