import { useState } from "react";

const CITIES = ["Алматы", "Астана", "Шымкент", "Караганда", "Атырау"];

type Sub = {
  city: string;
  priceMax: number;
  months: number;
};

type Props = {
  onSubscribe: (text: string) => void;
};

/**
 * Subscription panel. A client subscribes to a city and price segment for a 2 to 3 month
 * window and receives reminders when new matching objects appear. The list is kept in
 * local state for the demo; production persists it via the subscriptions module.
 */
export default function SubscriptionPanel({ onSubscribe }: Props) {
  const [city, setCity] = useState(CITIES[0]);
  const [priceMax, setPriceMax] = useState(30000000);
  const [months, setMonths] = useState(3);
  const [subs, setSubs] = useState<Sub[]>([]);

  const add = () => {
    const next = { city, priceMax, months };
    setSubs((s) => [...s, next]);
    onSubscribe(
      `Подписка оформлена: ${city}, до ${priceMax.toLocaleString("ru-KZ")} ₸, ${months} мес. Пришлём новые варианты.`,
    );
  };

  const remove = (i: number) => setSubs((s) => s.filter((_, idx) => idx !== i));

  return (
    <section className="panel">
      <h3>Подписка на новые объекты</h3>
      <div className="sub-grid">
        <select value={city} onChange={(e) => setCity(e.target.value)} aria-label="Город подписки">
          {CITIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <input
          type="number"
          value={priceMax}
          onChange={(e) => setPriceMax(Number(e.target.value))}
          aria-label="Максимальная цена"
        />
        <select
          value={months}
          onChange={(e) => setMonths(Number(e.target.value))}
          aria-label="Срок подписки"
        >
          <option value={2}>2 месяца</option>
          <option value={3}>3 месяца</option>
        </select>
        <button className="btn primary" onClick={add}>
          Подписаться
        </button>
      </div>
      {subs.length > 0 && (
        <ul className="sub-list">
          {subs.map((s, i) => (
            <li key={i}>
              {s.city}, до {s.priceMax.toLocaleString("ru-KZ")} ₸, {s.months} мес.
              <button className="btn ghost small" onClick={() => remove(i)}>
                Отменить
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
