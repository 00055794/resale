import { useEffect, useState } from "react";
import { calcMortgage, type MortgageResult } from "../api";
import { formatKzt, formatPct } from "../format";

type Props = {
  objectPrice: number;
};

/**
 * Mortgage calculator with co-borrower support and multi-bank comparison.
 *
 * Calls POST /calc/mortgage. The backend returns one scenario per bank plus a
 * debt-to-income (КДН) affordable payment cap that accounts for the co-borrower
 * income. HalykBank (lowest effective rate) is highlighted in the results table.
 *
 * Input ranges follow HalykBank's standard mortgage product: minimum down
 * payment 20%, maximum term 20 years — so moving a slider always changes the
 * HalykBank result rather than being silently capped by the backend.
 */
export default function Calculator({ objectPrice }: Props) {
  const HALYK_MIN_DOWN_PCT = 20;
  const HALYK_MAX_TERM_YEARS = 20;
  const DTI = 0.5; // КДН cap used for the affordability verdict.

  const [downPct, setDownPct] = useState(HALYK_MIN_DOWN_PCT);
  const [termYears, setTermYears] = useState(HALYK_MAX_TERM_YEARS);
  const [income, setIncome] = useState(850000);
  const [coIncome, setCoIncome] = useState(0);
  const [result, setResult] = useState<MortgageResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const downPayment = Math.round((objectPrice * downPct) / 100);

  // Calculate on mount and whenever any input changes, so the table and the
  // affordability verdict (income + co-borrower) always reflect the controls.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    calcMortgage({
      object_price: objectPrice,
      down_payment: downPayment,
      term_months: termYears * 12,
      income_kzt_month: income,
      coborrower_income_kzt_month: coIncome,
    })
      .then((r) => !cancelled && setResult(r))
      .catch((e) => !cancelled && setError(String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [objectPrice, downPayment, termYears, income, coIncome]);

  return (
    <div className="calc">
      <div className="calc-grid">
        <label>
          Первоначальный взнос: {downPct}% ({formatKzt(downPayment)})
          <input
            type="range"
            min={HALYK_MIN_DOWN_PCT}
            max={50}
            value={downPct}
            onChange={(e) => setDownPct(Number(e.target.value))}
          />
        </label>
        <label>
          Срок: {termYears} лет
          <input
            type="range"
            min={5}
            max={HALYK_MAX_TERM_YEARS}
            value={termYears}
            onChange={(e) => setTermYears(Number(e.target.value))}
          />
        </label>
        <label>
          Доход в месяц, ₸
          <input
            type="number"
            value={income}
            onChange={(e) => setIncome(Number(e.target.value))}
          />
        </label>
        <label>
          Доход созаёмщика, ₸
          <input
            type="number"
            value={coIncome}
            onChange={(e) => setCoIncome(Number(e.target.value))}
          />
        </label>
      </div>
      {loading && <p className="muted">Расчёт…</p>}
      {error && <p role="alert">Ошибка: {error}</p>}

      {result && (
        <div className="calc-result">
          {(() => {
            const halyk =
              result.scenarios.find((s) => s.bank_code === result.best_bank) ??
              result.scenarios[0];
            const totalIncome = income + coIncome;
            // Affordable monthly payment from income (КДН/DTI limit). This is the
            // installment the borrower can service and it moves with income and
            // co-borrower income.
            const affordablePayment = result.affordable_monthly_payment;
            const fits = halyk.monthly_payment <= affordablePayment;
            const kdn = totalIncome > 0 ? halyk.monthly_payment / totalIncome : 0;
            const minIncome = halyk.monthly_payment / DTI;
            // Inverse annuity: max loan HalykBank can service for that affordable
            // payment at the current rate and term -> max object price by income.
            const i = halyk.rate / 12;
            const n = halyk.term_months;
            const maxLoan =
              i > 0 ? (affordablePayment * (1 - Math.pow(1 + i, -n))) / i : affordablePayment * n;
            const maxObjectPrice =
              downPct < 100 ? maxLoan / (1 - downPct / 100) : maxLoan;
            return (
              <>
                <div className={`afford-verdict ${fits ? "ok" : "warn"}`}>
                  <p>
                    Платёж HalykBank: <strong>{formatKzt(halyk.monthly_payment)}</strong> / мес ·
                    комфортный платёж по доходу (КДН {Math.round(DTI * 100)}%):{" "}
                    <strong>{formatKzt(affordablePayment)}</strong>
                  </p>
                  <p>
                    По вашему доходу HalykBank профинансирует объект примерно до{" "}
                    <strong>{formatKzt(maxObjectPrice)}</strong>
                  </p>
                  <p className="muted">
                    {fits
                      ? `✓ Платёж укладывается в доход. Долговая нагрузка (КДН) ${formatPct(kdn)}.`
                      : `✗ Платёж превышает лимит (КДН ${formatPct(
                          kdn,
                        )}). Увеличьте взнос/срок или добавьте созаёмщика. Минимальный доход: ${formatKzt(
                          minIncome,
                        )}.`}
                  </p>
                </div>
                <p className="muted">
                  Платёж банка по выбранному объекту зависит от взноса, срока и ставки.
                  Доход и доход созаёмщика задают комфортный платёж (КДН) и максимальную
                  сумму финансирования. Лимиты HalykBank: взнос от {HALYK_MIN_DOWN_PCT}%,
                  срок до {HALYK_MAX_TERM_YEARS} лет.
                </p>
              </>
            );
          })()}
          <table className="banks-table">
            <thead>
              <tr>
                <th>Банк</th>
                <th>Ставка / ГЭСВ</th>
                <th>Взнос</th>
                <th>Срок</th>
                <th>Платёж/мес</th>
                <th>Переплата</th>
              </tr>
            </thead>
            <tbody>
              {result.scenarios
                .slice()
                .sort((a, b) => a.monthly_payment - b.monthly_payment)
                .map((s) => {
                  const best = s.bank_code === result.best_bank;
                  const affordable =
                    s.monthly_payment <= result.affordable_monthly_payment;
                  return (
                    <tr key={s.bank_code} className={best ? "best" : ""}>
                      <td>
                        {s.bank_name}
                        {best && <span className="badge green">Лучшее предложение</span>}
                      </td>
                      <td>
                        {formatPct(s.rate)}{" "}
                        <span className="muted">/ {formatPct(s.effective_annual_rate)}</span>
                      </td>
                      <td>{formatKzt(s.down_payment_applied)}</td>
                      <td>{Math.round(s.term_months / 12)} лет</td>
                      <td className={affordable ? "ok" : "warn"}>
                        {formatKzt(s.monthly_payment)}
                      </td>
                      <td>{formatKzt(s.overpayment)}</td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
          <p className="muted">
            ГЭСВ — годовая эффективная ставка вознаграждения (включает комиссии). Каждый банк
            применяет свой минимальный взнос и срок, поэтому суммы взноса и переплаты
            различаются. HalykBank остаётся лучшим предложением по платежу.
          </p>
        </div>
      )}
    </div>
  );
}
