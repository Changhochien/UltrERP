import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { useIsMobile } from "../../hooks/useIsMobile";

function MobileProbe() {
  const isMobile = useIsMobile();
  return <div data-testid="mobile-state">{isMobile ? "mobile" : "desktop"}</div>;
}

function setViewportMatch(width: number) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: query === "(max-width: 639px)" ? width <= 639 : false,
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => true,
    }),
  });
}

afterEach(() => {
  cleanup();
});

describe("useIsMobile", () => {
  it("treats phone widths as mobile", () => {
    setViewportMatch(639);
    render(<MobileProbe />);
    expect(screen.getByTestId("mobile-state").textContent).toBe("mobile");
  });

  it("treats tablet widths as desktop sidebar mode", () => {
    setViewportMatch(640);
    render(<MobileProbe />);
    expect(screen.getByTestId("mobile-state").textContent).toBe("desktop");
  });
});