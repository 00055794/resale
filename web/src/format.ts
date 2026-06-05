export function formatKzt(n: number): string {
  return new Intl.NumberFormat("ru-KZ", { maximumFractionDigits: 0 }).format(n) + " ₸";
}

export function discountPct(bank: number, market: number): number {
  if (market <= 0) return 0;
  return Math.round((1 - bank / market) * 1000) / 10;
}

export function savingsKzt(bank: number, market: number): number {
  return Math.max(0, Math.round(market - bank));
}

export function formatPct(fraction: number): string {
  return (Math.round(fraction * 1000) / 10).toFixed(1) + "%";
}

export function regionFromIin(iin: string): string | null {
  // ИИН positions 1-6 are the birth date; region is not encoded in ИИН.
  // We use a documented fallback table keyed by the issuing-region demo prefix.
  // Real wiring resolves region via the SSO client profile.
  const map: Record<string, string> = {
    "75": "Алматы",
    "71": "Астана",
    "59": "Шымкент",
    "30": "Караганда",
    "23": "Атырау",
  };
  const cleaned = iin.replace(/\D/g, "");
  if (cleaned.length < 12) return null;
  return map[cleaned.slice(10, 12)] ?? null;
}

export function whatsappShareUrl(flatId: string, address: string, price: number): string {
  const text = `Залоговая квартира: ${address}, цена ${formatKzt(price)}. Подробнее в Homebank: https://homebank.kz/services/resale/${flatId}`;
  return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

export function shareUrl(flatId: string): string {
  return `https://homebank.kz/services/resale/${flatId}`;
}
