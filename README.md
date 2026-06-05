# ReSALE

Встроенный модуль каталога залоговой недвижимости HalykBank внутри Homebank (раздел "Сервисы").
Источник данных: halykzalog.kz. MVP: квартиры на балансе банка.

Цели: повысить конверсию из просмотра в ипотечную сделку, сократить срок реализации залогов,
встроить аукционный сценарий ("Оставить заявку") и AI-отчёт по объекту.

## Architecture

Monorepo:

```
resale/
  report/        Самодостаточный HTML-отчёт: интерактивный альбом из 3 страниц
                 (Портфель банка · Прототип модели · Реальность) с анимированными
                 графиками и кликабельным мобильным прототипом. Открывается двойным
                 кликом, без сборки.
  web/           Веб-приложение (React + TypeScript + Vite)
  server/        Backend API (FastAPI + Python 3.11)
  docs/          Архитектура, бизнес-кейс, API, безопасность, QA, питч
  assets/        Брендинг, фото квартир (источник: halykzalog.kz)
  .github/       CI/CD pipelines
```

См. [docs/architecture.md](docs/architecture.md), [docs/business-case.md](docs/business-case.md),
[docs/api-spec.md](docs/api-spec.md), [docs/security.md](docs/security.md),
[docs/qa-test-plan.md](docs/qa-test-plan.md), [docs/pitch-outline.md](docs/pitch-outline.md).

## Quick start

Demo report (no install required):

```
open resale/report/index.html      # обзорный дашборд (3-page album)
open resale/report/index1.html     # финальный дашборд для питча
```

### View the dashboard online (GitHub Pages)

The `report/` folder is published automatically by `.github/workflows/pages.yml`.
After enabling Pages once (repo **Settings → Pages → Source: GitHub Actions**), the
dashboards open in any browser:

- Overview: `https://gulikz.github.io/resale/`
- Final pitch dashboard: `https://gulikz.github.io/resale/index1.html`

No-setup alternative (renders the committed HTML directly):
`https://htmlpreview.github.io/?https://github.com/gulikz/resale/blob/main/report/index1.html`

### Run with Docker (full stack)

```
docker compose up --build
```

- `web`  → http://localhost:8080  (nginx, собранный React build)
- `server`→ http://localhost:8000  (FastAPI, `/docs`, `/metrics`, `/health`)
- `db` (PostgreSQL 16) + `cache` (Redis 7) поднимаются автоматически.
- `.env` не требуется — образ работает на mock-адаптерах; при наличии `.env`
  (`cp .env.example .env`) переменные подхватываются автоматически.

### Run locally without Docker

Backend:

```
cd server
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate на *nix)
pip install -r requirements.txt
uvicorn app.main:app --reload     # http://localhost:8000
pytest                            # 14 тестов
```

Frontend (Node.js 18+):

```
cd web
npm install
npm run dev                       # http://localhost:5173
npm run build && npm test
```

## Status

- Catalog, filters (city, rooms, price, income cap, geotag, ИИН-region fallback), list/map toggle,
  object card: implemented in `web/` and `report/`.
- Object detail modal with tabs (Обзор, Сравнение цен, GenAI отчёт, Калькулятор, Оставить заявку):
  implemented in `web/src/components/ObjectModal.tsx`.
- Map view with pins: `web/src/components/MapView.tsx`. Google Maps embed when
  `VITE_GOOGLE_MAPS_API_KEY` is set; self-contained SVG fallback (offline demo) otherwise.
- Price comparison vs krisha.kz: implemented via `KrishaPriceAdapter` (mock; real source documented).
- GenAI investment report: implemented via `GenAIAdapter` (mock; OpenAI-compatible interface).
- Mortgage / auction calculator with co-borrower and multi-bank comparison: implemented in
  `server/app/calc.py` with tests, surfaced in `web/src/components/Calculator.tsx` and `report/`.
- Economic effect model (Conservative / Realistic / Optimistic): `server/app/calc.py`.
- Halyk SSO, CBS push: interfaces in `server/app/integrations.py`, mock adapters for demo;
  SSO login bar in `web/src/components/LoginBar.tsx`.
- Reminders + subscription (2-3 month, city + price segment): `web/src/components/SubscriptionPanel.tsx`
  plus reminders feed in `web/src/App.tsx`.
- Share + WhatsApp share: implemented in `web/src/format.ts` and surfaced on cards and in the modal.
- CI (lint + test + build): `.github/workflows/ci.yml`.

## Observability & security

- **Logging**: структурированные логи запросов (`method route -> status id=<request-id> elapsed_ms`)
  через middleware в `server/app/main.py`.
- **Metrics**: эндпоинт `GET /metrics` отдаёт счётчики в формате Prometheus
  (`resale_requests_total`, `resale_request_latency_seconds_*`); включается флагом
  `METRICS_ENABLED`.
- **Health/readiness**: `GET /health`, `GET /ready` (с режимами адаптеров) — используются
  в Docker healthcheck и k8s probes.
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
  на каждом ответе; `X-Request-Id` для трассировки.
- **CORS**: список доменов задаётся `ALLOWED_ORIGINS` (по умолчанию — только localhost
  dev-порты, не `*`).
- **Validation**: все входные данные проходят через Pydantic-модели; идемпотентность
  CBS-запросов по `Idempotency-Key`.

См. [docs/security.md](docs/security.md).

## License

Internal HalykBank prototype. See [LICENSE](LICENSE).
