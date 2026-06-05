from app.calc import (
    annuity_payment,
    effect_scenarios,
    effective_annual_rate,
    max_affordable_payment,
    mortgage_scenario,
)


def test_annuity_payment_zero_rate():
    assert annuity_payment(120_000, 0.0, 12) == 10_000


def test_annuity_payment_known_value():
    # 1,000,000 at 12% for 12 months -> ~88,849
    pmt = annuity_payment(1_000_000, 0.12, 12)
    assert 88_000 < pmt < 90_000


def test_mortgage_scenario_overpayment_positive():
    s = mortgage_scenario(
        bank_code="halyk", bank_name="HalykBank",
        object_price=20_000_000, down_payment=4_000_000,
        annual_rate=0.165, term_months=240, fee_pct=0.0,
    )
    assert s.monthly_payment > 0
    assert s.overpayment > 0
    assert s.total_paid > 16_000_000
    # Down payment is reported back transparently; principal = price - down (no fee).
    assert s.down_payment_applied == 4_000_000
    assert s.principal == 16_000_000
    assert s.financed_fee == 0.0


def test_mortgage_scenario_financed_fee_raises_effective_rate():
    no_fee = mortgage_scenario(
        bank_code="a", bank_name="A", object_price=20_000_000, down_payment=5_000_000,
        annual_rate=0.18, term_months=240, fee_pct=0.0,
    )
    with_fee = mortgage_scenario(
        bank_code="b", bank_name="B", object_price=20_000_000, down_payment=5_000_000,
        annual_rate=0.18, term_months=240, fee_pct=0.01,
    )
    # A financed fee increases principal and the true cost (ГЭСВ).
    assert with_fee.financed_fee > 0
    assert with_fee.principal > no_fee.principal
    assert with_fee.effective_annual_rate > no_fee.effective_annual_rate


def test_effective_annual_rate_above_nominal():
    # ГЭСВ from monthly compounding exceeds the nominal annual rate.
    pmt = annuity_payment(16_000_000, 0.165, 240)
    eff = effective_annual_rate(16_000_000, pmt, 240)
    assert 0.165 < eff < 0.185


def test_max_affordable_payment_includes_coborrower():
    assert max_affordable_payment(800_000, 400_000, dti=0.5) == 600_000


def test_effect_scenarios_order_and_shape():
    scs = effect_scenarios(
        avg_monthly_apps=1271, leakage=0.10, p_win=0.40,
        tr_mortgage=0.51, avg_mortgage_rate=0.165,
        max_mortgage_rate=0.205, avg_product_rate=0.115,
        avg_loan_kzt=20_000_000, margin_pct=0.02,
    )
    names = [s.name for s in scs]
    assert names == ["conservative", "realistic", "optimistic"]
    # Optimistic >= realistic >= conservative on disbursements
    assert scs[2].monthly_disbursements >= scs[1].monthly_disbursements >= scs[0].monthly_disbursements


def test_effect_take_rate_capped():
    scs = effect_scenarios(
        avg_monthly_apps=1000, tr_mortgage=0.9,
        avg_mortgage_rate=1.0, max_mortgage_rate=2.0, avg_product_rate=0.1,
    )
    for s in scs:
        assert 0.0 <= s.take_rate <= 1.0
