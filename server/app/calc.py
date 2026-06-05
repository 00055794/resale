"""Mortgage and effect calculators.

Pure functions, fully unit-tested. No I/O.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MortgageScenario:
    bank_code: str
    bank_name: str
    rate: float
    term_months: int
    monthly_payment: float
    total_paid: float
    overpayment: float


def annuity_payment(principal: float, annual_rate: float, term_months: int) -> float:
    """Standard annuity (аннуитетный платёж)."""
    if principal <= 0 or term_months <= 0:
        return 0.0
    if annual_rate <= 0:
        return principal / term_months
    r = annual_rate / 12.0
    factor = (r * (1 + r) ** term_months) / ((1 + r) ** term_months - 1)
    return principal * factor


def mortgage_scenario(
    *,
    bank_code: str,
    bank_name: str,
    object_price: float,
    down_payment: float,
    annual_rate: float,
    term_months: int,
    fee_pct: float = 0.0,
) -> MortgageScenario:
    principal = max(0.0, object_price - down_payment) * (1.0 + fee_pct)
    pmt = annuity_payment(principal, annual_rate, term_months)
    total = pmt * term_months
    return MortgageScenario(
        bank_code=bank_code,
        bank_name=bank_name,
        rate=annual_rate,
        term_months=term_months,
        monthly_payment=round(pmt, 2),
        total_paid=round(total, 2),
        overpayment=round(total - principal, 2),
    )


def max_affordable_payment(income: float, coborrower_income: float = 0.0, dti: float = 0.5) -> float:
    """Debt-to-income capped monthly payment."""
    total_income = max(0.0, income) + max(0.0, coborrower_income)
    return total_income * dti


# ----- Economic effect model -----


@dataclass(frozen=True)
class EffectScenario:
    name: str
    take_rate: float
    monthly_disbursements: int
    monthly_revenue_kzt: float
    annual_revenue_kzt: float


def effect_scenarios(
    *,
    avg_monthly_apps: int,
    leakage: float = 0.10,
    p_win: float = 0.40,
    tr_mortgage: float = 0.51,
    avg_mortgage_rate: float = 0.165,
    max_mortgage_rate: float = 0.205,
    avg_product_rate: float = 0.115,
    avg_loan_kzt: float = 20_000_000,
    margin_pct: float = 0.02,
) -> list[EffectScenario]:
    """Three scenarios per the documented methodology.

    Conservative: TR == TR_mortgage (понижает оценку, т.к. ставка по продукту ниже).
    Realistic:    TR == TR_mortgage * (avg_mortgage_rate / avg_product_rate).
    Optimistic:   TR == TR_mortgage * (max_mortgage_rate / avg_product_rate).
    """
    requests = max(0.0, avg_monthly_apps) * (1.0 - leakage)

    def build(name: str, tr: float) -> EffectScenario:
        tr_capped = max(0.0, min(1.0, tr))
        disb = int(round(requests * p_win * tr_capped))
        monthly_rev = disb * avg_loan_kzt * margin_pct
        return EffectScenario(
            name=name,
            take_rate=round(tr_capped, 4),
            monthly_disbursements=disb,
            monthly_revenue_kzt=round(monthly_rev, 2),
            annual_revenue_kzt=round(monthly_rev * 12, 2),
        )

    return [
        build("conservative", tr_mortgage),
        build("realistic", tr_mortgage * (avg_mortgage_rate / max(avg_product_rate, 1e-9))),
        build("optimistic", tr_mortgage * (max_mortgage_rate / max(avg_product_rate, 1e-9))),
    ]
