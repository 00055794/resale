# API specification (OpenAPI 3.1, summary)

Full spec is served by the backend at `GET /openapi.json` (FastAPI auto-generated).
Swagger UI: `GET /docs`. ReDoc: `GET /redoc`.

## Endpoints (MVP)

```
GET    /catalog                          List flats with filters
       query: city, price_min, price_max, area_min, area_max, rooms,
              income_cap, geo (lat,lng,radius_km), iin_region, page, size, sort

GET    /catalog/{id}                     Object detail (Bank-checked, photos, geo, price)

GET    /comparison/{id}                  { bank_price, krisha_median, discount_pct, comparables[] }

GET    /genai/report/{id}                Personalized investment report
       headers: X-Profile-Hash (derived from session)

POST   /calc/mortgage                    Mortgage scenarios with optional co-borrower
       body:   { object_id, down_payment, term_months, income, coborrower? }
       returns scenarios for HalykBank + competitor banks

POST   /calc/effect                      Economic effect model
       body:   { requests, p_win, tr_mortgage, avg_mortgage_rate, avg_product_rate, ... }
       returns conservative / realistic / optimistic disbursements and revenue

POST   /auctions/{id}/bids               Place / re-place an auction bid
GET    /auctions/{id}                    Auction state, participants, time-to-start, avg wait
POST   /cbs/mortgage                     Push pre-filled mortgage application to CBS (idempotent)

GET    /subscriptions                    List user subscriptions
POST   /subscriptions                    { city, price_min, price_max, months }
DELETE /subscriptions/{id}

GET    /reminders                        Active reminders for the user

POST   /auth/sso/exchange                Exchange Homebank SSO token for ReSALE session
GET    /me                               Current user profile (masked PII)

GET    /health                           Liveness
GET    /ready                            Readiness (checks DB, Redis, integrations)
GET    /metrics                          Prometheus metrics
```

## Conventions

- All responses JSON UTF-8. Errors use RFC 7807 problem+json.
- Idempotency: `Idempotency-Key` header required for POST `/cbs/mortgage` and `/auctions/.../bids`.
- Rate limit: 60 rpm per user, 600 rpm per IP. 429 on breach with `Retry-After`.
- Auth: Bearer JWT from Halyk SSO. Scopes: `resale.read`, `resale.write`, `resale.mortgage`.
- PII (ИИН, доход) маскируется в логах и ответах списочных эндпоинтов.
