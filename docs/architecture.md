# Architecture

## Context (C4 L1)

```
[Homebank mobile app] --(SSO + deep link)--> [ReSALE module]
[ReSALE web]          --(REST + GraphQL)--> [ReSALE API]
[ReSALE API]          --> [PostgreSQL] [Redis]
[ReSALE API]          --> [Halyk SSO] [CBS] [Google Maps] [Krisha adapter] [GenAI]
```

## Containers (C4 L2)

- `web/` (React + TS + Vite). SSR-ready (Next.js migration documented). Static assets via CDN.
- `server/` (FastAPI). Stateless. Behind load balancer. Horizontal autoscale on CPU + RPS.
- PostgreSQL 16 (primary catalog, applications, subscriptions, audit log).
- Redis 7 (search cache, rate limiting, idempotency keys, session cache).
- Object storage (S3-compatible) for flat photos.
- Message bus (Kafka or RabbitMQ) for reminders and event sourcing.

## Components (C4 L3) — server

- `catalog` lists/filters/sorts collateral objects, geo-search.
- `comparison` computes discount vs krisha.kz comparable price.
- `genai` produces personalized investment report. Caches per (object_id, profile_hash).
- `calc` mortgage + auction calculator, co-borrower aware, multi-bank comparison.
- `effect` economic-effect model (conservative / realistic / optimistic).
- `auctions` "Оставить заявку", participant tracking, re-participation discount.
- `reminders` schedules and dispatches notifications (auction start, new interest, etc.).
- `subscriptions` 2-3 month user subscriptions to city + price segment.
- `auth` Halyk SSO OIDC client.
- `integrations` adapters: `HalykSSOAdapter`, `CBSAdapter`, `GoogleMapsAdapter`,
  `KrishaPriceAdapter`, `GenAIAdapter`. Each has a `Mock*` implementation used when
  `*_MODE=mock`.

## Data flow

1. Client opens Homebank, taps "Сервисы > ReSALE". SSO token is exchanged for ReSALE session.
2. Web requests `/catalog` with filters (price, type, location, ИИН-region fallback, income cap).
3. For each card, `/comparison/{id}` returns Bank price, krisha median, discount %.
4. On card open, `/genai/report/{id}` returns cached or freshly generated investment report.
5. `/calc/mortgage` computes scenarios; `/calc/effect` returns business effect for the dashboard.
6. "Оставить заявку" -> `/auctions/{id}/bids` (auction) and/or `/cbs/mortgage` (mortgage push).

## Scalability (target 100k+ concurrent)

- Stateless API behind L7 LB; autoscaling groups (min 4, max 64) on RPS and p95 latency.
- Redis caching: catalog list keys TTL 60s; object detail TTL 300s; GenAI report TTL 24h.
- Postgres read replicas for catalog reads; connection pool via PgBouncer.
- Virtualized lists + image lazy loading in web; bundle code-split per route.
- Map tiles via Google Maps quota with per-user rate limiting; cluster pins server-side.
- Backpressure: token-bucket rate limiter per IP + per user, circuit breaker on integrations.
- Observability: structured JSON logs, Prometheus metrics, OpenTelemetry traces.

## Failure modes and degradation

- GenAI down -> show cached report or template summary with disclaimer.
- Krisha adapter down -> hide comparison panel, keep catalog.
- CBS down -> queue application in outbox, retry with idempotency key.
- Maps quota exceeded -> fall back to static tile snapshot.

## Deployment

- Containerized (Docker). Kubernetes manifests / Helm chart (out of MVP scope, placeholder).
- Environments: dev, staging, prod. Blue/green for API. Feature flags via env.
