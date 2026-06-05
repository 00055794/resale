# QA / Auditor checklist

## Acceptance criteria (MVP)

- [ ] Catalog returns >= 700 flats from seed, with valid photos and geo.
- [ ] Filters: city, price range, area, rooms, income cap, geo radius, ИИН-region fallback.
- [ ] List <-> map toggle with clustered pins.
- [ ] Object card shows Bank-checked badge, photos carousel, price, comparison panel.
- [ ] Comparison panel shows bank price, krisha median, discount %, 3+ comparables.
- [ ] GenAI report opens on card view; rendered <= 3s (cache hit) / <= 8s (cold).
- [ ] Mortgage calculator: term, down payment, income, co-borrower; multi-bank comparison table.
- [ ] Economic effect model returns 3 scenarios with the documented formula.
- [ ] "Оставить заявку" (auction) creates a bid; re-participation discount applied if not winner.
- [ ] Subscription creation with 2-3 month duration; reminders fire on new matches.
- [ ] Share button and WhatsApp share produce deep link with utm parameters.
- [ ] Halyk SSO login flow works end-to-end (mock adapter in demo).
- [ ] CBS push is idempotent and retried with backoff on 5xx.

## Non-functional

- [ ] p95 catalog list latency <= 250 ms with cache warm.
- [ ] Web LCP <= 2.5s on 4G profile.
- [ ] WCAG AA: contrast, keyboard nav, ARIA on interactive elements.
- [ ] RU primary, EN fallback strings present.
- [ ] No console errors in demo flows.

## Security

- [ ] No secrets in repo (`gitleaks` clean).
- [ ] Auth required on all non-public endpoints.
- [ ] PII masked in logs.
- [ ] Rate limiting verified with k6 script.
- [ ] CSP, HSTS, X-Frame-Options headers present.

## CI

- [ ] Lint passes (web + server).
- [ ] Type checks pass (tsc, mypy).
- [ ] Tests pass with meaningful coverage on `calc`, `effect`, `comparison`.
- [ ] Build artifacts produced.

## Test matrix

| Flow                       | Unit | Integration | E2E |
|----------------------------|------|-------------|-----|
| Catalog filters            |  x   |     x       |  x  |
| Comparison panel           |  x   |     x       |     |
| Mortgage calculator        |  x   |     x       |  x  |
| Effect model               |  x   |             |     |
| Auction bid + re-bid       |  x   |     x       |  x  |
| Subscription + reminder    |  x   |     x       |     |
| SSO exchange               |  x   |     x       |     |
| CBS push idempotency       |  x   |     x       |     |
