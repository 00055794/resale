const API = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

export type Flat = {
  id: string;
  type: string;
  city: string;
  district: string;
  address: string;
  rooms: number;
  area: number;
  floor: number;
  floors: number;
  year: number;
  bank_price: number;
  market_price: number;
  lat: number;
  lng: number;
  bank_checked: boolean;
  photo: string;
  photos?: string[];
  geo_precise?: boolean;
  building_type?: string;
  condition?: string;
  url?: string;
};

export type CatalogResponse = { total: number; page: number; size: number; items: Flat[] };

export type Comparable = { price: number; area: number; rooms: number };

export type Comparison = {
  flat_id: string;
  bank_price: number;
  krisha_median: number;
  discount_pct: number;
  comparables: Comparable[];
  source: string;
};

export type GenAIReport = { flat_id: string; report: string; model: string };

export type MortgageScenario = {
  bank_code: string;
  bank_name: string;
  rate: number;
  effective_annual_rate: number;
  term_months: number;
  down_payment_applied: number;
  principal: number;
  financed_fee: number;
  monthly_payment: number;
  total_paid: number;
  overpayment: number;
};

export type MortgageResult = {
  affordable_monthly_payment: number;
  best_bank: string;
  scenarios: MortgageScenario[];
};

export type MortgageInput = {
  object_price: number;
  down_payment: number;
  term_months: number;
  income_kzt_month: number;
  coborrower_income_kzt_month: number;
};

export type BidResult = {
  flat_id: string;
  accepted: boolean;
  effective_bid: number;
  reentry_discount_pct: number;
  avg_wait_days_to_start: number;
  participants_estimate: number;
};

export type CbsResult = { status: string; cbs_ref: string; queue_position: number };

async function getJson<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json() as Promise<T>;
}

export function fetchCatalog(
  params: Record<string, string | number | undefined>,
): Promise<CatalogResponse> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  });
  return getJson<CatalogResponse>(`/catalog?${qs.toString()}`);
}

export function fetchComparison(flatId: string): Promise<Comparison> {
  return getJson<Comparison>(`/comparison/${flatId}`);
}

export function fetchGenAIReport(flatId: string): Promise<GenAIReport> {
  return getJson<GenAIReport>(`/genai/report/${flatId}`);
}

export function calcMortgage(input: MortgageInput): Promise<MortgageResult> {
  return postJson<MortgageResult>(`/calc/mortgage`, input);
}

export function placeBid(
  flatId: string,
  bidKzt: number,
  isReentry: boolean,
): Promise<BidResult> {
  return postJson<BidResult>(`/auctions/${flatId}/bids`, {
    flat_id: flatId,
    bid_kzt: bidKzt,
    is_reentry: isReentry,
  });
}

export function pushCbsMortgage(body: {
  flat_id: string;
  full_name: string;
  iin: string;
  income_kzt_month: number;
  down_payment: number;
  term_months: number;
}): Promise<CbsResult> {
  return postJson<CbsResult>(`/cbs/mortgage`, body);
}
