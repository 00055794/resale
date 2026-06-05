from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_security_headers_present():
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "X-Request-Id" in r.headers


def test_metrics_exposition():
    client.get("/health")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "resale_requests_total" in r.text


def test_catalog_filter_by_city():
    r = client.get("/catalog", params={"city": "Алматы", "size": 50})
    data = r.json()
    assert data["total"] > 0
    assert all(item["city"] == "Алматы" for item in data["items"])


def _first_flat_id() -> str:
    return client.get("/catalog", params={"size": 1}).json()["items"][0]["id"]


def test_comparison_returns_discount():
    r = client.get(f"/comparison/{_first_flat_id()}")
    data = r.json()
    assert "discount_pct" in data
    assert data["bank_price"] > 0


def test_calc_mortgage_compares_banks():
    r = client.post("/calc/mortgage", json={
        "object_price": 25_000_000, "down_payment": 5_000_000,
        "term_months": 240, "income_kzt_month": 800_000,
    })
    data = r.json()
    assert len(data["scenarios"]) >= 3
    assert data["best_bank"] == "halyk"


def test_calc_effect_three_scenarios():
    r = client.post("/calc/effect", json={})
    data = r.json()
    assert len(data["scenarios"]) == 3
    assert data["takerate"]["may_2026"]["take_rate"] == 0.51


def test_auction_reentry_discount():
    fid = _first_flat_id()
    r = client.post(f"/auctions/{fid}/bids", json={
        "flat_id": fid, "bid_kzt": 30_000_000, "is_reentry": True,
    })
    data = r.json()
    assert data["accepted"] is True
    assert data["reentry_discount_pct"] == 2.0
