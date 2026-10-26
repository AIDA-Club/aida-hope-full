import { describe, expect, it } from "vitest";
import { format, roundHalfEven, splitTemplate } from "./format";

describe("format", () => {
  it("fills plain and fixed-point fields like Python str.format", () => {
    expect(format("{label} · {percent:.0f}%", { label: "Normal", percent: 86.2 })).toBe("Normal · 86%");
    expect(format("Threshold: {threshold:.0f}%", { threshold: 50 })).toBe("Threshold: 50%");
    expect(format("Case {current} of {total}", { current: 1, total: 5 })).toBe("Case 1 of 5");
  });
  it("rounds halves to even, as Python does", () => {
    expect(roundHalfEven(0.5, 0)).toBe("0");
    expect(roundHalfEven(1.5, 0)).toBe("2");
    expect(roundHalfEven(2.5, 0)).toBe("2");
    expect(roundHalfEven(83.82, 0)).toBe("84");
  });
  it("leaves unknown fields alone", () => {
    expect(format("Hi {name}", {})).toBe("Hi {name}");
  });
  it("splits a template into text and fields", () => {
    expect(splitTemplate("Your answer: {answer}")).toEqual([{ text: "Your answer: " }, { field: "answer", digits: undefined }]);
  });
});
