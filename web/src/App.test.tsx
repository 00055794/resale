import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import App from "./App";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    fetchCatalog: vi.fn().mockResolvedValue({
      total: 1,
      page: 1,
      size: 60,
      items: [
        {
          id: "f-001",
          type: "flat",
          city: "Алматы",
          district: "Бостандык",
          address: "ул. Демо 1",
          rooms: 2,
          area: 60,
          floor: 5,
          floors: 9,
          year: 2015,
          bank_price: 30000000,
          market_price: 40000000,
          lat: 43.238,
          lng: 76.945,
          bank_checked: true,
          photo: "f-001.jpg",
        },
      ],
    }),
  };
});

describe("App catalog", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders a catalog card with bank-checked badge and discount", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText(/ул. Демо 1/)).toBeInTheDocument());
    expect(screen.getAllByText(/Проверено банком/).length).toBeGreaterThan(0);
    expect(screen.getByText(/-25% к рынку/)).toBeInTheDocument();
  });

  it("shows the subscription panel", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText(/Подписка на новые объекты/)).toBeInTheDocument());
  });
});
