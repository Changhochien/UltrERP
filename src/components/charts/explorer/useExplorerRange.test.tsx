import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useExplorerRange } from "./useExplorerRange";

describe("useExplorerRange", () => {
  it("keeps month precision when applying presets", () => {
    const { result } = renderHook(() =>
      useExplorerRange({
        availableRange: { start: "2023-01", end: "2026-04" },
        defaultVisibleRange: { start: "2025-05", end: "2026-04" },
        currentDate: new Date("2026-04-25T00:00:00Z"),
      }),
    );

    act(() => result.current.applyPreset("3M"));

    expect(result.current.visibleRange).toEqual({ start: "2026-02", end: "2026-04" });

    act(() => result.current.applyPreset("All"));

    expect(result.current.visibleRange).toEqual({ start: "2023-01", end: "2026-04" });
  });

  it("clamps custom visible ranges to the loaded range", () => {
    const { result } = renderHook(() =>
      useExplorerRange({
        availableRange: { start: "2026-01-01", end: "2026-01-31" },
        defaultVisibleRange: { start: "2026-01-10", end: "2026-01-20" },
        currentDate: new Date("2026-01-31T00:00:00Z"),
      }),
    );

    act(() => result.current.updateVisibleRange({ start: "2025-12-01", end: "2026-02-15" }));

    expect(result.current.visibleRange).toEqual({ start: "2026-01-01", end: "2026-01-31" });
    expect(result.current.selectedPreset).toBeNull();
  });
});