from __future__ import annotations

import logging
import math
import time
import uuid
from collections import defaultdict
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .calc import effect_scenarios, max_affordable_payment, mortgage_scenario
from .config import settings
from .data_loader import banks, edw_prices, flats, takerate
from .integrations import (
    MockCBSAdapter,
    MockGenAIAdapter,
    MockHalykSSOAdapter,
    MockKrishaPriceAdapter,
)

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("resale")

app = FastAPI(title="ReSALE API", version="0.1.0")

_allowed_origins = ["*"] if settings.allowed_origins.strip() == "*" else [
    o.strip() for o in settings.allowed_origins.split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# --- lightweight in-process metrics (Prometheus text exposition) ---
_metrics_requests: dict[tuple[str, int], int] = defaultdict(int)
_metrics_latency_sum: dict[str, float] = defaultdict(float)
_metrics_latency_count: dict[str, int] = defaultdict(int)

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


@app.middleware("http")
async def observability_middleware(request: Request, call_next: Any) -> Response:
    """Record request count/latency, attach a request id, and set security headers."""
    started = time.perf_counter()
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    route = request.url.path
    try:
        response: Response = await call_next(request)
    except Exception:
        elapsed = time.perf_counter() - started
        log.exception("request_failed id=%s %s %s elapsed_ms=%.1f", request_id, request.method, route, elapsed * 1000)
        if settings.metrics_enabled:
            _metrics_requests[(route, 500)] += 1
        raise
    elapsed = time.perf_counter() - started
    if settings.metrics_enabled:
        _metrics_requests[(route, response.status_code)] += 1
        _metrics_latency_sum[route] += elapsed
        _metrics_latency_count[route] += 1
    for key, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
    response.headers["X-Request-Id"] = request_id
    log.info("%s %s -> %s id=%s elapsed_ms=%.1f", request.method, route, response.status_code, request_id, elapsed * 1000)
    return response


_krisha = MockKrishaPriceAdapter()
_genai = MockGenAIAdapter()
_cbs = MockCBSAdapter()
_sso = MockHalykSSOAdapter()


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, Any]:
    return {"status": "ok", "modes": {"krisha": settings.krisha_scrape_mode, "cbs": settings.cbs_mode, "genai": settings.genai_mode}}


@app.get("/metrics")
def metrics() -> Response:
    """Prometheus text exposition of request counters and latency."""
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="metrics_disabled")
    lines = [
        "# HELP resale_requests_total Total HTTP requests by route and status.",
        "# TYPE resale_requests_total counter",
    ]
    for (route, status), count in sorted(_metrics_requests.items()):
        lines.append(f'resale_requests_total{{route="{route}",status="{status}"}} {count}')
    lines += [
        "# HELP resale_request_latency_seconds_sum Sum of request latency by route.",
        "# TYPE resale_request_latency_seconds_sum counter",
    ]
    for route, total in sorted(_metrics_latency_sum.items()):
        lines.append(f'resale_request_latency_seconds_sum{{route="{route}"}} {total:.6f}')
        lines.append(f'resale_request_latency_seconds_count{{route="{route}"}} {_metrics_latency_count[route]}')
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.get("/catalog")
def catalog(
    city: str | None = None,
    price_min: int = 0,
    price_max: int = 10**12,
    rooms: int | None = None,
    income_cap_payment: float | None = Query(None, description="Max monthly payment user can afford"),
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float = 5.0,
    iin_region: str | None = None,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    items = flats()
    if city:
        items = [f for f in items if f["city"].lower() == city.lower()]
    elif iin_region:
        items = [f for f in items if f["city"].lower() == iin_region.lower()]
    items = [f for f in items if price_min <= f["bank_price"] <= price_max]
    if rooms is not None:
        items = [f for f in items if f["rooms"] == rooms]
    if lat is not None and lng is not None:
        items = [f for f in items if _haversine_km(lat, lng, f["lat"], f["lng"]) <= radius_km]
    if income_cap_payment is not None and income_cap_payment > 0:
        # Filter where 20-year HalykBank payment fits the cap.
        halyk = next(b for b in banks()["banks"] if b["code"] == "halyk")
        capped = []
        for f in items:
            principal = f["bank_price"] * (1 - halyk["min_down_pct"])
            r = halyk["rate"] / 12
            n = 240
            pmt = principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
            if pmt <= income_cap_payment:
                capped.append(f)
        items = capped

    total = len(items)
    start = (page - 1) * size
    return {"total": total, "page": page, "size": size, "items": items[start:start + size]}


@app.get("/catalog/{flat_id}")
def catalog_item(flat_id: str) -> dict[str, Any]:
    for f in flats():
        if f["id"] == flat_id:
            return f
    raise HTTPException(status_code=404, detail="not_found")


@app.get("/comparison/{flat_id}")
def comparison(flat_id: str) -> dict[str, Any]:
    flat = catalog_item(flat_id)
    edw = edw_prices().get(flat_id)
    if edw and edw.get("market_median_kzt"):
        median = int(edw["market_median_kzt"])
        comparables = [
            {"price": int(median * 0.96), "area": flat["area"] - 1.0, "rooms": flat["rooms"]},
            {"price": int(median * 1.02), "area": flat["area"] + 0.5, "rooms": flat["rooms"]},
            {"price": int(median * 1.08), "area": flat["area"] + 2.0, "rooms": flat["rooms"]},
        ]
        source = f"edw://{edw.get('method', 'edw')}"
    else:
        cmp = _krisha.comparables(city=flat["city"], rooms=flat["rooms"], area=flat["area"])
        median = cmp["median_kzt"]
        comparables = cmp["comparables"]
        source = cmp["source"]
    discount = 1.0 - flat["bank_price"] / max(median, 1)
    return {
        "flat_id": flat_id,
        "bank_price": flat["bank_price"],
        "krisha_median": median,
        "discount_pct": round(discount * 100, 1),
        "comparables": comparables,
        "source": source,
    }


@app.get("/genai/report/{flat_id}")
def genai_report(flat_id: str) -> dict[str, Any]:
    flat = catalog_item(flat_id)
    profile = _sso.exchange(token="demo")
    text = _genai.investment_report(flat=flat, profile=profile)
    return {"flat_id": flat_id, "report": text, "model": settings.genai_model}


class MortgageRequest(BaseModel):
    object_price: float = Field(gt=0)
    down_payment: float = Field(ge=0)
    term_months: int = Field(gt=0, le=360)
    income_kzt_month: float = Field(ge=0)
    coborrower_income_kzt_month: float = Field(default=0.0, ge=0)


@app.post("/calc/mortgage")
def calc_mortgage(req: MortgageRequest) -> dict[str, Any]:
    scenarios = [
        mortgage_scenario(
            bank_code=b["code"],
            bank_name=b["name"],
            object_price=req.object_price,
            down_payment=max(req.down_payment, req.object_price * b["min_down_pct"]),
            annual_rate=b["rate"],
            term_months=min(req.term_months, b["max_term_months"]),
            fee_pct=b["fee_pct"],
        )
        for b in banks()["banks"]
    ]
    cap = max_affordable_payment(req.income_kzt_month, req.coborrower_income_kzt_month)
    best = min(scenarios, key=lambda s: s.monthly_payment)
    return {
        "affordable_monthly_payment": round(cap, 2),
        "best_bank": best.bank_code,
        "scenarios": [s.__dict__ for s in scenarios],
    }


class EffectRequest(BaseModel):
    avg_monthly_apps: int = 1271
    leakage: float = 0.10
    p_win: float = 0.40
    tr_mortgage: float = 0.51
    avg_mortgage_rate: float = 0.165
    max_mortgage_rate: float = 0.205
    avg_product_rate: float = 0.115
    avg_loan_kzt: float = 20_000_000
    margin_pct: float = 0.02


@app.post("/calc/effect")
def calc_effect(req: EffectRequest) -> dict[str, Any]:
    scenarios = effect_scenarios(**req.model_dump())
    return {"scenarios": [s.__dict__ for s in scenarios], "takerate": takerate()}


class CBSPushRequest(BaseModel):
    flat_id: str
    full_name: str
    iin: str
    income_kzt_month: float
    down_payment: float
    term_months: int


@app.post("/cbs/mortgage")
def cbs_push(req: CBSPushRequest, idempotency_key: str | None = None) -> dict[str, Any]:
    key = idempotency_key or str(uuid.uuid4())
    log.info("cbs_push flat=%s key=%s", req.flat_id, key)
    return _cbs.push_mortgage(application=req.model_dump(), idempotency_key=key)


class AuctionBidRequest(BaseModel):
    flat_id: str
    bid_kzt: float
    is_reentry: bool = False


@app.post("/auctions/{flat_id}/bids")
def place_bid(flat_id: str, req: AuctionBidRequest) -> dict[str, Any]:
    discount = 0.02 if req.is_reentry else 0.0
    effective = req.bid_kzt * (1 - discount)
    return {
        "flat_id": flat_id,
        "accepted": True,
        "effective_bid": round(effective, 2),
        "reentry_discount_pct": discount * 100,
        "avg_wait_days_to_start": 7,
        "participants_estimate": 2,
    }
