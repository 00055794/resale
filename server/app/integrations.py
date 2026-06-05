"""Integration adapters with mock implementations.

In `*_MODE=mock` (default for demo) we return deterministic synthetic data so the
application is fully usable offline. Real adapters wire HTTP clients to live providers.
"""
from __future__ import annotations

import hashlib
from typing import Any, Protocol


class KrishaPriceAdapter(Protocol):
    def comparables(self, *, city: str, rooms: int, area: float) -> dict[str, Any]: ...


class MockKrishaPriceAdapter:
    def comparables(self, *, city: str, rooms: int, area: float) -> dict[str, Any]:
        # Deterministic synthetic median based on inputs.
        base = 250_000 if city in {"Алматы", "Астана"} else 180_000
        median = int(base * area * (1.0 + 0.05 * rooms))
        return {
            "median_kzt": median,
            "sample_size": 24,
            "source": "mock://krisha.kz",
            "comparables": [
                {"price": int(median * 0.96), "area": area - 1.0, "rooms": rooms},
                {"price": int(median * 1.02), "area": area + 0.5, "rooms": rooms},
                {"price": int(median * 1.08), "area": area + 2.0, "rooms": rooms},
            ],
        }


class GenAIAdapter(Protocol):
    def investment_report(self, *, flat: dict[str, Any], profile: dict[str, Any]) -> str: ...


class MockGenAIAdapter:
    def investment_report(self, *, flat: dict[str, Any], profile: dict[str, Any]) -> str:
        discount = 1.0 - flat["bank_price"] / max(flat["market_price"], 1)
        return (
            f"Объект {flat['address']}, {flat['city']}. "
            f"Цена банка {flat['bank_price']:,} ₸, рыночная медиана {flat['market_price']:,} ₸. "
            f"Дисконт {discount*100:.1f}%. Объект проверен банком. "
            f"При горизонте 5 лет ожидаемая доходность от перепродажи 18-25% годовых "
            f"в базовом сценарии, аренда покрывает 60-75% ипотечного платежа."
        ).replace(",", " ")


class CBSAdapter(Protocol):
    def push_mortgage(self, *, application: dict[str, Any], idempotency_key: str) -> dict[str, Any]: ...


class MockCBSAdapter:
    def push_mortgage(self, *, application: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        ref = hashlib.sha1(idempotency_key.encode()).hexdigest()[:10].upper()
        return {"status": "accepted", "cbs_ref": f"MTG-{ref}", "queue_position": 1}


class HalykSSOAdapter(Protocol):
    def exchange(self, *, token: str) -> dict[str, Any]: ...


class MockHalykSSOAdapter:
    def exchange(self, *, token: str) -> dict[str, Any]:
        return {
            "sub": "demo-user-001",
            "name": "Демо Клиент",
            "iin_region": "Алматы",
            "income_kzt_month": 850_000,
        }
