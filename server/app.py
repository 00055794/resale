"""ReSALE — Streamlit application.

A single-file Streamlit UI that mirrors the full React web app **and** the
FastAPI backend, reusing the exact business logic from the ``app`` package
(``app.calc``, ``app.data_loader``, ``app.integrations``). No running API
server is required — every endpoint is reproduced in-process so the demo works
fully offline.

Run from ``resale/server``:

    streamlit run app.py

Functionality covered (parity with web/ + server/):
  • Halyk SSO login (mock) with profile personalisation
  • Catalog with city / rooms / price / income-cap / ИИН-region / geo filters
  • Stats: objects, average discount, total savings
  • List view (cards) and interactive map view (pydeck)
  • Object detail tabs: Обзор (GenAI report), Сравнение цен, Калькулятор, Заявка
  • Multi-bank mortgage calculator with КДН affordability verdict + max price
  • Auction bid (with re-entry discount) and CBS push
  • Subscriptions + reminders
  • Economic effect model (conservative / realistic / optimistic) + take-rate series
"""
from __future__ import annotations

import math
import sys
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

# Ensure the `app` package (this directory) is importable when Streamlit runs
# this file as __main__.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.calc import effect_scenarios, max_affordable_payment, mortgage_scenario  # noqa: E402
from app.data_loader import banks, edw_prices, flats, takerate  # noqa: E402
from app.integrations import (  # noqa: E402
    MockCBSAdapter,
    MockGenAIAdapter,
    MockHalykSSOAdapter,
    MockKrishaPriceAdapter,
)

# --- shared mock adapters (mirror server singletons) -----------------------
_krisha = MockKrishaPriceAdapter()
_genai = MockGenAIAdapter()
_cbs = MockCBSAdapter()
_sso = MockHalykSSOAdapter()

HALYK_GREEN = "#1f9b5b"
HALYK_YELLOW = "#f4c430"

CITIES = [
    "", "Алматы", "Астана", "Шымкент", "Караганда", "Атырау", "Актобе",
    "Актау", "Павлодар", "Петропавловск", "Кокшетау", "Уральск", "Костанай",
    "Тараз", "Кызылорда", "Семей", "Усть-Каменогорск", "Темиртау",
    "Экибастуз", "Жезказган",
]
PAGE_SIZE = 60


# ===========================================================================
# Formatting helpers (parity with web/src/format.ts)
# ===========================================================================
def format_kzt(n: float) -> str:
    return f"{round(n):,}".replace(",", " ") + " ₸"


def discount_pct(bank: float, market: float) -> float:
    if market <= 0:
        return 0.0
    return round((1 - bank / market) * 1000) / 10


def savings_kzt(bank: float, market: float) -> int:
    return max(0, round(market - bank))


def format_pct(fraction: float) -> str:
    return f"{round(fraction * 1000) / 10:.1f}%"


def region_from_iin(iin: str) -> str | None:
    table = {"75": "Алматы", "71": "Астана", "59": "Шымкент", "30": "Караганда", "23": "Атырау"}
    cleaned = "".join(ch for ch in iin if ch.isdigit())
    if len(cleaned) < 12:
        return None
    return table.get(cleaned[10:12])


def whatsapp_share_url(flat_id: str, address: str, price: float) -> str:
    from urllib.parse import quote

    text = (
        f"Залоговая квартира: {address}, цена {format_kzt(price)}. "
        f"Подробнее в Homebank: https://homebank.kz/services/resale/{flat_id}"
    )
    return f"https://wa.me/?text={quote(text)}"


def share_url(flat_id: str) -> str:
    return f"https://homebank.kz/services/resale/{flat_id}"


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ===========================================================================
# In-process "API" — mirrors server/app/main.py routes
# ===========================================================================
def api_catalog(
    *,
    city: str | None = None,
    price_min: int = 0,
    price_max: int = 10**12,
    rooms: int | None = None,
    income_cap_payment: float | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float = 5.0,
    iin_region: str | None = None,
) -> list[dict[str, Any]]:
    items = flats()
    if city:
        items = [f for f in items if f["city"].lower() == city.lower()]
    elif iin_region:
        items = [f for f in items if f["city"].lower() == iin_region.lower()]
    items = [f for f in items if price_min <= f["bank_price"] <= price_max]
    if rooms is not None:
        items = [f for f in items if f["rooms"] == rooms]
    if lat is not None and lng is not None:
        items = [f for f in items if haversine_km(lat, lng, f["lat"], f["lng"]) <= radius_km]
    if income_cap_payment is not None and income_cap_payment > 0:
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
    return items


def api_comparison(flat: dict[str, Any]) -> dict[str, Any]:
    edw = edw_prices().get(flat["id"])
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
        "bank_price": flat["bank_price"],
        "krisha_median": median,
        "discount_pct": round(discount * 100, 1),
        "comparables": comparables,
        "source": source,
    }


def api_genai_report(flat: dict[str, Any]) -> str:
    profile = _sso.exchange(token="demo")
    return _genai.investment_report(flat=flat, profile=profile)


def api_calc_mortgage(
    *, object_price: float, down_payment: float, term_months: int,
    income: float, coborrower_income: float,
) -> dict[str, Any]:
    scenarios = [
        mortgage_scenario(
            bank_code=b["code"],
            bank_name=b["name"],
            object_price=object_price,
            down_payment=max(down_payment, object_price * b["min_down_pct"]),
            annual_rate=b["rate"],
            term_months=min(term_months, b["max_term_months"]),
            fee_pct=b["fee_pct"],
        )
        for b in banks()["banks"]
    ]
    cap = max_affordable_payment(income, coborrower_income)
    best = min(scenarios, key=lambda s: s.effective_annual_rate)
    return {
        "affordable_monthly_payment": round(cap, 2),
        "best_bank": best.bank_code,
        "scenarios": [s.__dict__ for s in scenarios],
    }


def api_place_bid(*, bid_kzt: float, is_reentry: bool) -> dict[str, Any]:
    discount = 0.02 if is_reentry else 0.0
    return {
        "accepted": True,
        "effective_bid": round(bid_kzt * (1 - discount), 2),
        "reentry_discount_pct": discount * 100,
        "avg_wait_days_to_start": 7,
        "participants_estimate": 2,
    }


def api_cbs_push(application: dict[str, Any]) -> dict[str, Any]:
    return _cbs.push_mortgage(application=application, idempotency_key=str(uuid.uuid4()))


# ===========================================================================
# Session state
# ===========================================================================
def init_state() -> None:
    ss = st.session_state
    ss.setdefault("session", None)
    ss.setdefault("reminders", [])
    ss.setdefault("subscriptions", [])
    ss.setdefault("selected", None)
    ss.setdefault("page", 1)


def add_reminder(text: str) -> None:
    st.session_state.reminders = [text, *st.session_state.reminders][:5]


# ===========================================================================
# UI sections
# ===========================================================================
def render_login_sidebar() -> None:
    ss = st.session_state
    st.sidebar.subheader("Halyk SSO")
    if ss.session:
        st.sidebar.success(
            f"{ss.session['name']} · регион по ИИН: {ss.session['iinRegion']}"
        )
        if st.sidebar.button("Выйти", use_container_width=True):
            ss.session = None
            st.rerun()
    else:
        st.sidebar.caption("Войдите для персонализации (доход, регион).")
        if st.sidebar.button("Войти через Halyk SSO", type="primary", use_container_width=True):
            profile = _sso.exchange(token="demo")
            ss.session = {
                "name": profile["name"],
                "iinRegion": profile["iin_region"],
                "income": profile["income_kzt_month"],
            }
            st.rerun()


def render_filters() -> dict[str, Any]:
    ss = st.session_state
    st.sidebar.subheader("Фильтры каталога")
    city = st.sidebar.selectbox(
        "Город", CITIES, format_func=lambda c: c or "Все города", key="f_city"
    )
    rooms = st.sidebar.selectbox(
        "Комнат", ["", "1", "2", "3"], format_func=lambda r: r or "любое", key="f_rooms"
    )
    price_max = st.sidebar.number_input(
        "Цена до, ₸", min_value=0, value=0, step=1_000_000, key="f_price"
    )
    default_income = int(ss.session["income"]) if ss.session else 0
    income = st.sidebar.number_input(
        "Доход в месяц, ₸", min_value=0, value=default_income, step=50_000, key="f_income"
    )
    iin = st.sidebar.text_input("ИИН (регион)", max_chars=12, key="f_iin")
    use_geo = st.sidebar.checkbox("По геопозиции (Алматы, демо)", key="f_geo")

    iin_region = region_from_iin(iin)
    geo = {"lat": 43.238, "lng": 76.945} if use_geo else None
    effective_region = city or ("" if geo else (iin_region or ""))
    if iin_region and not city and not geo:
        st.sidebar.caption(f"Регион по ИИН: {iin_region}")

    return {
        "city": city or None,
        "iin_region": iin_region if (not city and not geo) else None,
        "rooms": int(rooms) if rooms else None,
        "price_max": int(price_max) if price_max else 10**12,
        "income_cap_payment": income * 0.5 if income else None,
        "geo": geo,
        "effective_region": effective_region,
    }


def render_subscriptions_sidebar() -> None:
    ss = st.session_state
    st.sidebar.subheader("Подписка на новые объекты")
    with st.sidebar.form("sub_form", clear_on_submit=True):
        sc = st.selectbox("Город", ["Алматы", "Астана", "Шымкент", "Караганда", "Атырау"])
        sp = st.number_input("Максимальная цена, ₸", min_value=0, value=30_000_000, step=1_000_000)
        sm = st.selectbox("Срок", [2, 3], format_func=lambda m: f"{m} месяца")
        if st.form_submit_button("Подписаться", use_container_width=True):
            ss.subscriptions.append({"city": sc, "priceMax": sp, "months": sm})
            add_reminder(
                f"Подписка оформлена: {sc}, до {format_kzt(sp)}, {sm} мес. Пришлём новые варианты."
            )
    for i, s in enumerate(ss.subscriptions):
        cols = st.sidebar.columns([4, 1])
        cols[0].caption(f"{s['city']}, до {format_kzt(s['priceMax'])}, {s['months']} мес.")
        if cols[1].button("✕", key=f"unsub_{i}"):
            ss.subscriptions.pop(i)
            st.rerun()


def render_reminders() -> None:
    if st.session_state.reminders:
        with st.container(border=True):
            st.markdown("**Напоминания**")
            for r in st.session_state.reminders:
                st.write("• " + r)


def render_stats(items: list[dict[str, Any]], total: int) -> None:
    avg_disc = (
        round(sum(discount_pct(f["bank_price"], f["market_price"]) for f in items) / len(items))
        if items else 0
    )
    total_savings = sum(savings_kzt(f["bank_price"], f["market_price"]) for f in items)
    c1, c2, c3 = st.columns(3)
    c1.metric("Объектов", total)
    c2.metric("Средний дисконт", f"{avg_disc}%")
    c3.metric("Совокупная экономия", format_kzt(total_savings))


def render_card(flat: dict[str, Any]) -> None:
    disc = discount_pct(flat["bank_price"], flat["market_price"])
    savings = savings_kzt(flat["bank_price"], flat["market_price"])
    with st.container(border=True):
        if flat.get("photo"):
            st.image(flat["photo"], use_column_width=True)
        st.markdown(
            f"<span style='background:{HALYK_GREEN};color:#fff;padding:2px 8px;border-radius:10px;"
            f"font-size:12px'>Проверено банком</span> "
            f"<span style='background:{HALYK_YELLOW};color:#3a2f00;padding:2px 8px;border-radius:10px;"
            f"font-size:12px'>-{disc}% к рынку</span>",
            unsafe_allow_html=True,
        )
        st.markdown(f"### {format_kzt(flat['bank_price'])}")
        st.caption(f"Экономия {format_kzt(savings)}")
        st.caption(
            f"{flat['rooms']} комн · {flat['area']} м² · "
            f"{flat['floor']}/{flat['floors']} эт · {flat['year']}"
        )
        st.caption(f"{flat['address']}, {flat['city']}")
        b1, b2 = st.columns(2)
        if b1.button("Оставить заявку", key=f"open_{flat['id']}", type="primary",
                     use_container_width=True):
            st.session_state.selected = flat["id"]
            st.rerun()
        b2.link_button(
            "WhatsApp",
            whatsapp_share_url(flat["id"], flat["address"], flat["bank_price"]),
            use_container_width=True,
        )


def render_list(items: list[dict[str, Any]], total: int) -> None:
    cols_per_row = 3
    for row_start in range(0, len(items), cols_per_row):
        row = items[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, flat in zip(cols, row):
            with col:
                render_card(flat)
    if len(items) < total:
        if st.button(f"Показать ещё ({len(items)} из {total})", use_container_width=True):
            st.session_state.page += 1
            st.rerun()


def render_map(items: list[dict[str, Any]]) -> None:
    pts = [
        {
            "lat": f["lat"],
            "lng": f["lng"],
            "label": f"{f['bank_price'] / 1_000_000:.1f} млн ₸",
            "address": f["address"],
            "rooms": f["rooms"],
            "disc": discount_pct(f["bank_price"], f["market_price"]),
        }
        for f in items
        if isinstance(f.get("lat"), (int, float)) and isinstance(f.get("lng"), (int, float))
    ]
    if not pts:
        st.info("Нет объектов с координатами для отображения на карте.")
        return
    df = pd.DataFrame(pts)
    try:
        import pydeck as pdk

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position="[lng, lat]",
            get_fill_color=[31, 155, 91, 180],
            get_radius=600,
            radius_min_pixels=4,
            pickable=True,
        )
        view = pdk.ViewState(
            latitude=float(df["lat"].mean()),
            longitude=float(df["lng"].mean()),
            zoom=4.5,
        )
        st.pydeck_chart(
            pdk.Deck(
                layers=[layer],
                initial_view_state=view,
                map_style=None,
                tooltip={"text": "{label}\n{address}\n{rooms} комн · -{disc}%"},
            )
        )
    except Exception:
        st.map(df.rename(columns={"lng": "lon"})[["lat", "lon"]])
    st.caption(f"Объектов на карте: {len(pts)}")


def render_object_detail(flat: dict[str, Any]) -> None:
    disc = discount_pct(flat["bank_price"], flat["market_price"])
    savings = savings_kzt(flat["bank_price"], flat["market_price"])

    if st.button("← Назад к каталогу"):
        st.session_state.selected = None
        st.rerun()

    st.markdown(
        f"<span style='background:{HALYK_GREEN};color:#fff;padding:2px 8px;border-radius:10px;"
        f"font-size:12px'>Проверено банком</span> "
        f"<span style='background:{HALYK_YELLOW};color:#3a2f00;padding:2px 8px;border-radius:10px;"
        f"font-size:12px'>-{disc}% к рынку</span>",
        unsafe_allow_html=True,
    )
    st.header(flat["address"])
    st.caption(
        f"{flat['city']}, {flat.get('district', '')} · {flat['rooms']} комн · "
        f"{flat['area']} м² · {flat['floor']}/{flat['floors']} эт · {flat['year']}"
    )

    tab_o, tab_c, tab_k, tab_a = st.tabs(
        ["Обзор", "Сравнение цен", "Калькулятор", "Оставить заявку"]
    )

    with tab_o:
        photos = flat.get("photos") or ([flat["photo"]] if flat.get("photo") else [])
        if photos:
            st.image(photos[:6], width=220)
        st.success(
            f"Цена банка **{format_kzt(flat['bank_price'])}**. "
            f"Экономия против рынка: **{format_kzt(savings)}** ({disc}%)."
        )
        cols = st.columns(2)
        cols[0].link_button(
            "Поделиться в WhatsApp",
            whatsapp_share_url(flat["id"], flat["address"], flat["bank_price"]),
            use_container_width=True,
        )
        cols[1].code(share_url(flat["id"]), language=None)
        st.caption(
            "Объект находится на балансе банка и проверен. Документы подготовлены, "
            "история залога прозрачна."
        )
        st.markdown("**Инвестиционный анализ (GenAI)**")
        st.info(api_genai_report(flat))

    with tab_c:
        cmp = api_comparison(flat)
        c1, c2 = st.columns(2)
        c1.metric("Залоговая цена банка", format_kzt(cmp["bank_price"]))
        c2.metric("Рынок krisha.kz (медиана)", format_kzt(cmp["krisha_median"]))
        st.success(f"Дисконт **{cmp['discount_pct']}%**")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Сопоставимые": format_kzt(c["price"]),
                        "Площадь": f"{c['area']} м²",
                        "Комнат": c["rooms"],
                    }
                    for c in cmp["comparables"]
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

    with tab_k:
        render_calculator(flat["bank_price"])

    with tab_a:
        render_auction(flat)


def render_calculator(object_price: float) -> None:
    HALYK_MIN_DOWN_PCT = 20
    HALYK_MAX_TERM_YEARS = 20
    DTI = 0.5

    c1, c2 = st.columns(2)
    down_pct = c1.slider("Первоначальный взнос, %", HALYK_MIN_DOWN_PCT, 50, HALYK_MIN_DOWN_PCT)
    term_years = c2.slider("Срок, лет", 5, HALYK_MAX_TERM_YEARS, HALYK_MAX_TERM_YEARS)
    c3, c4 = st.columns(2)
    income = c3.number_input("Доход в месяц, ₸", min_value=0, value=850_000, step=50_000)
    co_income = c4.number_input("Доход созаёмщика, ₸", min_value=0, value=0, step=50_000)

    down_payment = round(object_price * down_pct / 100)
    st.caption(f"Первоначальный взнос: {down_pct}% ({format_kzt(down_payment)})")

    result = api_calc_mortgage(
        object_price=object_price,
        down_payment=down_payment,
        term_months=term_years * 12,
        income=income,
        coborrower_income=co_income,
    )
    scenarios = result["scenarios"]
    halyk = next((s for s in scenarios if s["bank_code"] == result["best_bank"]), scenarios[0])
    total_income = income + co_income
    affordable = result["affordable_monthly_payment"]
    fits = halyk["monthly_payment"] <= affordable
    kdn = halyk["monthly_payment"] / total_income if total_income > 0 else 0
    min_income = halyk["monthly_payment"] / DTI
    i = halyk["rate"] / 12
    n = halyk["term_months"]
    max_loan = (affordable * (1 - (1 + i) ** (-n)) / i) if i > 0 else affordable * n
    max_object_price = max_loan / (1 - down_pct / 100) if down_pct < 100 else max_loan

    verdict = (
        f"Платёж HalykBank: **{format_kzt(halyk['monthly_payment'])}** / мес · "
        f"комфортный платёж по доходу (КДН {round(DTI * 100)}%): **{format_kzt(affordable)}**\n\n"
        f"По вашему доходу HalykBank профинансирует объект примерно до "
        f"**{format_kzt(max_object_price)}**"
    )
    if fits:
        st.success(verdict + f"\n\n✓ Платёж укладывается в доход. Долговая нагрузка (КДН) {format_pct(kdn)}.")
    else:
        st.warning(
            verdict
            + f"\n\n✗ Платёж превышает лимит (КДН {format_pct(kdn)}). Увеличьте взнос/срок или "
            f"добавьте созаёмщика. Минимальный доход: {format_kzt(min_income)}."
        )

    rows = sorted(scenarios, key=lambda s: s["monthly_payment"])
    table = pd.DataFrame(
        [
            {
                "Банк": s["bank_name"] + (" ⭐" if s["bank_code"] == result["best_bank"] else ""),
                "Ставка / ГЭСВ": f"{format_pct(s['rate'])} / {format_pct(s['effective_annual_rate'])}",
                "Взнос": format_kzt(s["down_payment_applied"]),
                "Срок": f"{round(s['term_months'] / 12)} лет",
                "Платёж/мес": format_kzt(s["monthly_payment"]),
                "Переплата": format_kzt(s["overpayment"]),
            }
            for s in rows
        ]
    )
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.caption(
        "ГЭСВ — годовая эффективная ставка вознаграждения (включает комиссии). "
        "HalykBank остаётся лучшим предложением по платежу."
    )


def render_auction(flat: dict[str, Any]) -> None:
    st.caption(
        "Основной способ покупки залогового объекта: участие в аукционе. "
        "Оставьте заявку, чтобы участвовать в торгах."
    )
    bid = st.number_input("Ваша ставка, ₸", min_value=0, value=int(flat["bank_price"]), step=100_000)
    reentry = st.checkbox("Повторное участие (скидка для не выигравших ранее)")
    if st.button("Оставить заявку", type="primary"):
        r = api_place_bid(bid_kzt=bid, is_reentry=reentry)
        msg = f"Заявка принята. Эффективная ставка: **{format_kzt(r['effective_bid'])}**"
        if r["reentry_discount_pct"] > 0:
            msg += f" (скидка повторного участия {r['reentry_discount_pct']}%)"
        st.success(msg)
        st.caption(
            f"Среднее ожидание до старта аукциона: {r['avg_wait_days_to_start']} дн. "
            f"Участников ориентировочно: {r['participants_estimate']}."
        )
        add_reminder(
            f"Заявка по объекту {flat['address']} принята. "
            f"Старт аукциона примерно через {r['avg_wait_days_to_start']} дн."
        )

    with st.expander("Отправить ипотечную заявку в CBS"):
        with st.form("cbs_form"):
            full_name = st.text_input("ФИО", value=(st.session_state.session or {}).get("name", ""))
            iin = st.text_input("ИИН", max_chars=12)
            income = st.number_input("Доход в месяц, ₸", min_value=0, value=850_000, step=50_000)
            down = st.number_input("Первоначальный взнос, ₸", min_value=0,
                                   value=int(flat["bank_price"] * 0.2), step=100_000)
            term = st.number_input("Срок, мес.", min_value=12, max_value=240, value=240, step=12)
            if st.form_submit_button("Отправить в CBS"):
                res = api_cbs_push(
                    {
                        "flat_id": flat["id"],
                        "full_name": full_name,
                        "iin": iin,
                        "income_kzt_month": income,
                        "down_payment": down,
                        "term_months": int(term),
                    }
                )
                st.success(
                    f"Статус: {res['status']} · CBS Ref: {res['cbs_ref']} · "
                    f"позиция в очереди: {res['queue_position']}"
                )


def render_dashboard_page() -> None:
    """Embed the static report dashboard (report/index2.html)."""
    import streamlit.components.v1 as components

    report = Path(__file__).resolve().parent.parent / "report" / "index2.html"
    st.header("Дашборд")
    if not report.exists():
        st.error(f"Файл не найден: {report}")
        return
    html = report.read_text(encoding="utf-8")
    # Resolve relative asset paths against the report folder so local images
    # (assets/…) load when the HTML is embedded in the Streamlit iframe.
    base_href = report.parent.as_uri() + "/"
    if "<base " not in html and "<head>" in html:
        html = html.replace("<head>", f'<head><base href="{base_href}">', 1)
    components.html(html, height=900, scrolling=True)
    st.caption(f"Источник: {report.name} · report/")


def render_effect_page() -> None:
    st.header("Экономический эффект")
    st.caption("Модель: три сценария (консервативный / реалистичный / оптимистичный).")
    tr = takerate()

    with st.expander("Параметры модели", expanded=False):
        c1, c2, c3 = st.columns(3)
        avg_apps = c1.number_input("Заявок в месяц", min_value=0, value=1271, step=10)
        leakage = c2.slider("Утечка (leakage)", 0.0, 0.5, 0.10, 0.01)
        p_win = c3.slider("Вероятность выигрыша", 0.0, 1.0, 0.40, 0.01)
        c4, c5, c6 = st.columns(3)
        tr_mortgage = c4.slider("TR ипотека", 0.0, 1.0, 0.51, 0.01)
        avg_mortgage_rate = c5.number_input("Средняя ставка ипотеки", value=0.165, step=0.001, format="%.3f")
        max_mortgage_rate = c6.number_input("Макс. ставка ипотеки", value=0.205, step=0.001, format="%.3f")
        c7, c8, c9 = st.columns(3)
        avg_product_rate = c7.number_input("Средняя ставка продукта", value=0.115, step=0.001, format="%.3f")
        avg_loan = c8.number_input("Средний кредит, ₸", min_value=0, value=20_000_000, step=1_000_000)
        margin = c9.slider("Маржа", 0.0, 0.10, 0.02, 0.005)

    scenarios = effect_scenarios(
        avg_monthly_apps=int(avg_apps),
        leakage=leakage,
        p_win=p_win,
        tr_mortgage=tr_mortgage,
        avg_mortgage_rate=avg_mortgage_rate,
        max_mortgage_rate=max_mortgage_rate,
        avg_product_rate=avg_product_rate,
        avg_loan_kzt=avg_loan,
        margin_pct=margin,
    )
    names = {"conservative": "Консервативный", "realistic": "Реалистичный", "optimistic": "Оптимистичный"}
    cols = st.columns(3)
    for col, s in zip(cols, scenarios):
        with col:
            st.subheader(names.get(s.name, s.name))
            st.metric("Take-rate", f"{s.take_rate * 100:.1f}%")
            st.metric("Выдач/мес", f"{s.monthly_disbursements}")
            st.metric("Доход/мес", format_kzt(s.monthly_revenue_kzt))
            st.metric("Доход/год", format_kzt(s.annual_revenue_kzt))

    st.subheader("Динамика take-rate")
    series = pd.DataFrame(tr["series"]).set_index("month")
    st.line_chart(series["take_rate"])
    st.caption(f"Источник: {tr['source']} · на {tr['as_of']}")


# ===========================================================================
# Main
# ===========================================================================
def main() -> None:
    st.set_page_config(page_title="ReSALE · Залоговая недвижимость", layout="wide")
    init_state()

    st.markdown(
        "## 🟢 ReSALE · Залоговая недвижимость "
        "<span style='font-size:14px;color:#888'>Halyk · Homebank · Сервисы</span>",
        unsafe_allow_html=True,
    )

    render_login_sidebar()
    st.sidebar.divider()
    page = st.sidebar.radio("Раздел", ["Каталог", "Экономический эффект", "Дашборд"])
    st.sidebar.divider()

    if page == "Дашборд":
        render_dashboard_page()
        return

    if page == "Экономический эффект":
        render_effect_page()
        return

    filters = render_filters()
    st.sidebar.divider()
    render_subscriptions_sidebar()

    # Reset pagination when filters change.
    fingerprint = (
        filters["city"], filters["rooms"], filters["price_max"],
        filters["income_cap_payment"], filters["iin_region"],
        bool(filters["geo"]),
    )
    if st.session_state.get("_fp") != fingerprint:
        st.session_state["_fp"] = fingerprint
        st.session_state.page = 1

    geo = filters["geo"]
    all_items = api_catalog(
        city=filters["city"],
        price_max=filters["price_max"],
        rooms=filters["rooms"],
        income_cap_payment=filters["income_cap_payment"],
        lat=geo["lat"] if geo else None,
        lng=geo["lng"] if geo else None,
        radius_km=1000 if geo else 5.0,
        iin_region=filters["iin_region"],
    )
    total = len(all_items)
    visible = all_items[: st.session_state.page * PAGE_SIZE]

    # Object detail view takes over when a flat is selected.
    selected_id = st.session_state.selected
    if selected_id:
        flat = next((f for f in flats() if f["id"] == selected_id), None)
        if flat:
            render_object_detail(flat)
            return
        st.session_state.selected = None

    render_stats(visible, total)
    if filters["effective_region"] and not filters["city"]:
        st.caption(f"Регион по ИИН: {filters['effective_region']}")
    render_reminders()

    view = st.radio("Вид", ["Списком", "На карте"], horizontal=True, label_visibility="collapsed")
    if view == "На карте":
        render_map(visible)
    else:
        if visible:
            render_list(visible, total)
        else:
            st.info("По заданным фильтрам объекты не найдены.")


if __name__ == "__main__":
    main()
