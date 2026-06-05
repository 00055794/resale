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
 * debt-to-income affordable payment cap that accounts for the co-borrower income.
 * HalykBank (the best offer) is highlighted in the results table.
 */
export default function Calculator({ objectPrice }: Props) {
  const [downPct, setDownPct] = useState(20);
  const [termYears, setTermYears] = useState(20);
  const [income, setIncome] = useState(850000);
  const [coIncome, setCoIncome] = useState(0);
  const [result, setResult] = useState<MortgageResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const downPayment = Math.round((objectPrice * downPct) / 100);

  const run = () => {
    setLoading(true);
    setError(null);
    calcMortgage({
      object_price: objectPrice,
      down_payment: downPayment,
      term_months: termYears * 12,
      income_kzt_month: income,
      coborrower_income_kzt_month: coIncome,
    })
      .then(setResult)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  // Once a result exists, keep it in sync as any input changes so the
  // affordability verdict (income + co-borrower) updates live.
  useEffect(() => {
    if (!result) return;
    let cancelled = false;
    calcMortgage({
      object_price: objectPrice,
      down_payment: downPayment,
      term_months: termYears * 12,
      income_kzt_month: income,
      coborrower_income_kzt_month: coIncome,
    })
      .then((r) => !cancelled && setResult(r))
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [objectPrice, downPayment, termYears, income, coIncome]);

  return (
    <div className="calc">
      <div className="calc-grid">
        <label>
          Первоначальный взнос: {downPct}% ({formatKzt(downPayment)})
          <input
            type="range"
            min={10}
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
            max={25}
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
      <button className="btn primary" onClick={run} disabled={loading}>
        {loading ? "Расчёт..." : "Рассчитать"}
      </button>
      {error && <p role="alert">Ошибка: {error}</p>}

      {result && (
        <div className="calc-result">
          {(() => {
            const halyk =
              result.scenarios.find((s) => s.bank_code === result.best_bank) ??
              result.scenarios[0];
            const fits = halyk.monthly_payment <= result.affordable_monthly_payment;
            return (
              <div className={`afford-verdict ${fits ? "ok" : "warn"}`}>
                <p>
                  Платёж HalykBank: <strong>{formatKzt(halyk.monthly_payment)}</strong> / мес ·
                  доступно по доходу: <strong>{formatKzt(result.affordable_monthly_payment)}</strong>
                </p>
                <p className="muted">
                  {fits
                    ? "✓ Платёж укладывается в ваш доход (с учётом созаёмщика)."
                    : "✗ Платёж превышает доступный лимит. Увеличьте взнос, срок или доход/созаёмщика."}
                </p>
              </div>
            );
          })()}
          <p className="muted">
            Размер платежа зависит от взноса, срока и ставки. Доход и доход созаёмщика
            определяют доступный лимит платежа (приемлемость), а не сам платёж.
          </p>
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
