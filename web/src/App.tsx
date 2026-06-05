import { useEffect, useMemo, useState } from "react";
import { fetchCatalog, type Flat } from "./api";
import { discountPct, formatKzt, regionFromIin, savingsKzt, whatsappShareUrl } from "./format";
import MapView from "./components/MapView";
import ObjectModal from "./components/ObjectModal";
import SubscriptionPanel from "./components/SubscriptionPanel";
import LoginBar, { type Session } from "./components/LoginBar";

const CITIES = ["", "Алматы", "Астана", "Шымкент", "Караганда", "Атырау"];

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [city, setCity] = useState("");
  const [rooms, setRooms] = useState<string>("");
  const [priceMax, setPriceMax] = useState<string>("");
  const [income, setIncome] = useState<string>("");
  const [iin, setIin] = useState<string>("");
  const [geo, setGeo] = useState<{ lat: number; lng: number } | null>(null);
  const [view, setView] = useState<"list" | "map">("list");
  const [items, setItems] = useState<Flat[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Flat | null>(null);
  const [reminders, setReminders] = useState<string[]>([]);

  // Location priority: primary geotag, secondary ИИН region. City filter overrides both.
  const iinRegion = useMemo(() => regionFromIin(iin), [iin]);
  const effectiveRegion = city || (geo ? "" : iinRegion || "");

  useEffect(() => {
    if (session) setIncome((v) => v || String(session.income));
  }, [session]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchCatalog({
      city: city || undefined,
      iin_region: !city && !geo ? iinRegion || undefined : undefined,
      rooms: rooms ? Number(rooms) : undefined,
      price_max: priceMax ? Number(priceMax) : undefined,
      income_cap_payment: income ? Number(income) * 0.5 : undefined,
      lat: geo?.lat,
      lng: geo?.lng,
      radius_km: geo ? 1000 : undefined,
      size: 60,
    })
      .then((d) => !cancelled && setItems(d.items))
      .catch((e) => !cancelled && setError(String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [city, rooms, priceMax, income, iinRegion, geo]);

  const avgDiscount = useMemo(() => {
    if (!items.length) return 0;
    return Math.round(
      items.reduce((a, f) => a + discountPct(f.bank_price, f.market_price), 0) / items.length,
    );
  }, [items]);

  const totalSavings = useMemo(
    () => items.reduce((a, f) => a + savingsKzt(f.bank_price, f.market_price), 0),
    [items],
  );

  const addReminder = (text: string) => setReminders((r) => [text, ...r].slice(0, 5));

  const useGeotag = () => {
    if (!navigator.geolocation) {
      setGeo({ lat: 43.238, lng: 76.945 }); // Almaty fallback
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => setGeo({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => setGeo({ lat: 43.238, lng: 76.945 }),
    );
  };

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <div className="brand-mark" /> ReSALE · Залоговая недвижимость
        </div>
        <div className="muted">Halyk · Homebank · Сервисы</div>
      </header>

      <LoginBar session={session} onLogin={setSession} onLogout={() => setSession(null)} />

      <div className="stats-row">
        <div className="stat">
          <span className="muted">Объектов</span>
          <strong>{items.length}</strong>
        </div>
        <div className="stat">
          <span className="muted">Средний дисконт</span>
          <strong style={{ color: "var(--halyk-green)" }}>{avgDiscount}%</strong>
        </div>
        <div className="stat">
          <span className="muted">Совокупная экономия</span>
          <strong>{formatKzt(totalSavings)}</strong>
        </div>
      </div>

      <div className="filters" role="search" aria-label="Фильтры каталога">
        <select aria-label="Город" value={city} onChange={(e) => setCity(e.target.value)}>
          {CITIES.map((c) => (
            <option key={c} value={c}>
              {c || "Все города"}
            </option>
          ))}
        </select>
        <select aria-label="Комнат" value={rooms} onChange={(e) => setRooms(e.target.value)}>
          <option value="">Комнат: любое</option>
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
        </select>
        <input
          type="number"
          placeholder="Цена до, ₸"
          value={priceMax}
          onChange={(e) => setPriceMax(e.target.value)}
        />
        <input
          type="number"
          placeholder="Доход в месяц, ₸"
          value={income}
          onChange={(e) => setIncome(e.target.value)}
        />
        <input
          type="text"
          placeholder="ИИН (регион)"
          value={iin}
          maxLength={12}
          onChange={(e) => setIin(e.target.value)}
          aria-label="ИИН для определения региона"
        />
        <button className="btn ghost" onClick={useGeotag}>
          {geo ? "Геопозиция включена" : "По геопозиции"}
        </button>
        <button className="btn primary" onClick={() => setView(view === "list" ? "map" : "list")}>
          {view === "list" ? "На карте" : "Списком"}
        </button>
      </div>

      {effectiveRegion && !city && (
        <p className="muted">Регион по ИИН: {effectiveRegion}</p>
      )}
      {error && <p role="alert">Ошибка: {error}. Убедитесь, что сервер запущен на :8000.</p>}
      {loading && <p>Загрузка...</p>}

      {reminders.length > 0 && (
        <section className="panel reminders">
          <h3>Напоминания</h3>
          <ul>
            {reminders.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </section>
      )}

      {view === "list" ? (
        <div className="grid">
          {items.map((f) => {
            const disc = discountPct(f.bank_price, f.market_price);
            return (
              <article key={f.id} className="card">
                <button className="photo" onClick={() => setSelected(f)} aria-label={`Открыть ${f.address}`}>
                  {f.photo ? <img src={f.photo} alt={f.address} loading="lazy" /> : null}
                  <span className="photo-city">{f.city}</span>
                </button>
                <div className="body">
                  <span className="badge green">Проверено банком</span>{" "}
                  <span className="badge yellow">-{disc}% к рынку</span>
                  <div className="price">{formatKzt(f.bank_price)}</div>
                  <div className="muted">
                    Экономия {formatKzt(savingsKzt(f.bank_price, f.market_price))}
                  </div>
                  <div className="muted">
                    {f.rooms} комн · {f.area} м² · {f.floor}/{f.floors} эт · {f.year}
                  </div>
                  <div className="muted">
                    {f.address}, {f.city}
                  </div>
                  <div className="card-actions">
                    <button className="btn primary" onClick={() => setSelected(f)}>
                      Оставить заявку
                    </button>
                    <a
                      className="btn secondary"
                      href={whatsappShareUrl(f.id, f.address, f.bank_price)}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      WhatsApp
                    </a>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <MapView items={items} onSelect={setSelected} />
      )}

      <SubscriptionPanel onSubscribe={addReminder} />

      {selected && (
        <ObjectModal flat={selected} onClose={() => setSelected(null)} onReminder={addReminder} />
      )}
    </div>
  );
}
