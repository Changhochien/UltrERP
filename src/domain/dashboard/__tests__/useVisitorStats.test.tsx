import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";

import { useVisitorStats } from "../hooks/useDashboard";

const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("useVisitorStats", () => {
  it("does not start another poll while a prior request is still in flight", async () => {
    vi.useFakeTimers();

    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
      () => new Promise<Response>(() => {}),
    );

    renderHook(() => useVisitorStats());
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(REFRESH_INTERVAL_MS);
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("aborts the in-flight request on unmount", async () => {
    let capturedSignal: AbortSignal | null = null;

    vi.spyOn(globalThis, "fetch").mockImplementation((_input, init) => {
      capturedSignal = (init as RequestInit | undefined)?.signal ?? null;
      return new Promise<Response>(() => {});
    });

    const { unmount } = renderHook(() => useVisitorStats());

    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(1));
    expect(capturedSignal).not.toBeNull();
    expect(capturedSignal?.aborted).toBe(false);

    unmount();

    expect(capturedSignal?.aborted).toBe(true);
  });
});