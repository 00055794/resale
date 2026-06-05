import { describe, expect, it } from "vitest";
import {
  discountPct,
  formatKzt,
  formatPct,
  regionFromIin,
  savingsKzt,
  shareUrl,
  whatsappShareUrl,
} from "./format";

describe("format helpers", () => {
  it("formats KZT", () => {
    expect(formatKzt(1234567)).toMatch(/1.?234.?567/);
  });
  it("computes discount", () => {
    expect(discountPct(80, 100)).toBe(20);
    expect(discountPct(0, 0)).toBe(0);
  });
  it("computes savings", () => {
    expect(savingsKzt(80, 100)).toBe(20);
    expect(savingsKzt(120, 100)).toBe(0);
  });
  it("formats fraction as percent", () => {
    expect(formatPct(0.165)).toBe("16.5%");
  });
  it("resolves region from ИИН demo prefix", () => {
    expect(regionFromIin("900101350075")).toBe("Алматы");
    expect(regionFromIin("123")).toBeNull();
    expect(regionFromIin("900101350099")).toBeNull();
  });
  it("builds whatsapp url", () => {
    const u = whatsappShareUrl("f-1", "Алматы", 1000000);
    expect(u).toContain("wa.me");
    expect(u).toContain("f-1");
  });
  it("builds share url", () => {
    expect(shareUrl("f-1")).toContain("/resale/f-1");
  });
});
