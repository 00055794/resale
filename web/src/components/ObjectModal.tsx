import { useEffect, useState } from "react";
import {
  fetchComparison,
  fetchGenAIReport,
  placeBid,
  type BidResult,
  type Comparison,
  type Flat,
  type GenAIReport,
} from "../api";
import { discountPct, formatKzt, savingsKzt, shareUrl, whatsappShareUrl } from "../format";
import Calculator from "./Calculator";

type Props = {
  flat: Flat;
  onClose: () => void;
  onReminder: (text: string) => void;
};

type Tab = "overview" | "comparison" | "genai" | "calc" | "auction";

export default function ObjectModal({ flat, onClose, onReminder }: Props) {
  const [tab, setTab] = useState<Tab>("overview");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [report, setReport] = useState<GenAIReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [bid, setBid] = useState<string>(String(flat.bank_price));
  const [reentry, setReentry] = useState(false);
  const [bidResult, setBidResult] = useState<BidResult | null>(null);

  useEffect(() => {
    fetchComparison(flat.id).then(setComparison).catch(() => setComparison(null));
  }, [flat.id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const loadReport = () => {
    setReportLoading(true);
    fetchGenAIReport(flat.id)
      .then(setReport)
      .finally(() => setReportLoading(false));
  };

  const submitBid = () => {
    placeBid(flat.id, Number(bid), reentry).then((r) => {
      setBidResult(r);
      onReminder(
        `Заявка по объекту ${flat.address} принята. Старт аукциона примерно через ${r.avg_wait_days_to_start} дн.`,
      );
    });
  };

  const disc = discountPct(flat.bank_price, flat.market_price);
  const savings = savingsKzt(flat.bank_price, flat.market_price);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={`Объект ${flat.address}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div>
            <span className="badge green">Проверено банком</span>{" "}
            {flat.bank_checked && <span className="badge green">Проверено GenAI</span>}{" "}
            <span className="badge yellow">-{disc}% к рынку</span>
            <h2>{flat.address}</h2>
            <p className="muted">
              {flat.city}, {flat.district} · {flat.rooms} комн · {flat.area} м² ·{" "}
              {flat.floor}/{flat.floors} эт · {flat.year}
            </p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </div>

        <div className="tabs" role="tablist">
          {(
            [
              ["overview", "Обзор"],
              ["comparison", "Сравнение цен"],
              ["genai", "GenAI отчёт"],
              ["calc", "Калькулятор"],
              ["auction", "Оставить заявку"],
            ] as [Tab, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              role="tab"
              aria-selected={tab === key}
              className={`tab ${tab === key ? "tab-active" : ""}`}
              onClick={() => {
                setTab(key);
                if (key === "genai" && !report && !reportLoading) loadReport();
              }}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="modal-body">
          {tab === "overview" && (
            <div>
              <div className="savings-banner">
                Цена банка <strong>{formatKzt(flat.bank_price)}</strong>. Экономия против
                рынка: <strong>{formatKzt(savings)}</strong> ({disc}%).
              </div>
              <div className="share-row">
                <a
                  className="btn secondary"
                  href={whatsappShareUrl(flat.id, flat.address, flat.bank_price)}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Поделиться в WhatsApp
                </a>
                <button
                  className="btn ghost"
                  onClick={() => navigator.clipboard?.writeText(shareUrl(flat.id))}
                >
                  Скопировать ссылку
                </button>
              </div>
              <p className="muted">
                Объект находится на балансе банка и проверен. Документы подготовлены,
                история залога прозрачна.
              </p>
            </div>
          )}

          {tab === "comparison" && (
            <div className="compare">
              {!comparison && <p>Загрузка сравнения...</p>}
              {comparison && (
                <>
                  <div className="compare-cols">
                    <div className="compare-col halyk">
                      <p className="muted">Залоговая цена банка</p>
                      <div className="big">{formatKzt(comparison.bank_price)}</div>
                    </div>
                    <div className="compare-col market">
                      <p className="muted">Рынок krisha.kz (медиана)</p>
                      <div className="big">{formatKzt(comparison.krisha_median)}</div>
                    </div>
                  </div>
                  <div className="savings-banner">
                    Дисконт <strong>{comparison.discount_pct}%</strong>. Источник:{" "}
                    {comparison.source}
                  </div>
                  <table className="banks-table">
                    <thead>
                      <tr>
                        <th>Сопоставимые</th>
                        <th>Площадь</th>
                        <th>Комнат</th>
                      </tr>
                    </thead>
                    <tbody>
                      {comparison.comparables.map((c, i) => (
                        <tr key={i}>
                          <td>{formatKzt(c.price)}</td>
                          <td>{c.area} м²</td>
                          <td>{c.rooms}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </div>
          )}

          {tab === "genai" && (
            <div>
              {reportLoading && <p>Готовим инвестиционный отчёт...</p>}
              {report && (
                <div className="genai-report">
                  <p className="muted">Модель: {report.model}</p>
                  <p>{report.report}</p>
                </div>
              )}
              {!report && !reportLoading && (
                <button className="btn primary" onClick={loadReport}>
                  Сформировать отчёт
                </button>
              )}
            </div>
          )}

          {tab === "calc" && <Calculator objectPrice={flat.bank_price} />}

          {tab === "auction" && (
            <div className="auction">
              <p className="muted">
                Основной способ покупки залогового объекта: участие в аукционе. Оставьте
                заявку, чтобы участвовать в торгах.
              </p>
              <label>
                Ваша ставка, ₸
                <input
                  type="number"
                  value={bid}
                  onChange={(e) => setBid(e.target.value)}
                />
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={reentry}
                  onChange={(e) => setReentry(e.target.checked)}
                />
                Повторное участие (скидка для не выигравших ранее)
              </label>
              <button className="btn primary" onClick={submitBid}>
                Оставить заявку
              </button>
              {bidResult && (
                <div className="auction-result">
                  <p>
                    Заявка принята. Эффективная ставка:{" "}
                    <strong>{formatKzt(bidResult.effective_bid)}</strong>
                    {bidResult.reentry_discount_pct > 0 &&
                      ` (скидка повторного участия ${bidResult.reentry_discount_pct}%)`}
                  </p>
                  <p className="muted">
                    Среднее ожидание до старта аукциона:{" "}
                    {bidResult.avg_wait_days_to_start} дн. Участников ориентировочно:{" "}
                    {bidResult.participants_estimate}.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
