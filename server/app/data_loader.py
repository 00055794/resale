from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"


@lru_cache(maxsize=8)
def load_json(name: str) -> Any:
    path = DATA_DIR / name
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def flats() -> list[dict[str, Any]]:
    return list(load_json("flats.json")["items"])


def takerate() -> dict[str, Any]:
    return load_json("takerate.json")


def banks() -> dict[str, Any]:
    return load_json("banks.json")


def edw_prices() -> dict[str, Any]:
    """Market medians sourced from EDW / krisha.kz (separate file).

    Returns an empty mapping if the EDW export is not present, so callers can
    fall back to the krisha mock adapter.
    """
    try:
        return load_json("edw_prices.json").get("prices", {})
    except FileNotFoundError:
        return {}

