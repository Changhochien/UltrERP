import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { usePostHogPageView } from "../../hooks/usePostHogPageView";

vi.mock("../../lib/posthog", () => ({
  posthog: {
    __loaded: true,
    capture: vi.fn(),
  },
}));

function TestComponent() {
  usePostHogPageView();
  return <div>test</div>;
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.resetModules();
});

describe("usePostHogPageView", () => {
  it("captures pageview on mount when PostHog is loaded", async () => {
    const { posthog } = await import("../../lib/posthog");

    render(
      <MemoryRouter initialEntries={["/test"]}>
        <TestComponent />
      </MemoryRouter>,
    );

    expect(posthog.capture).toHaveBeenCalledWith(
      "$pageview",
      expect.objectContaining({
        $current_url: expect.any(String),
        $screen_width: expect.any(Number),
        $screen_height: expect.any(Number),
      }),
    );
  });

  it("does not throw when PostHog is not loaded", async () => {
    vi.doMock("../../lib/posthog", () => ({
      posthog: { __loaded: false, capture: vi.fn() },
    }));

    const mod = await import("../../hooks/usePostHogPageView");

    expect(() => {
      render(
        <MemoryRouter>
          <TestComponentWithHook hook={mod.usePostHogPageView} />
        </MemoryRouter>,
      );
    }).not.toThrow();
  });
});

function TestComponentWithHook({ hook }: { hook: () => void }) {
  hook();
  return <div>test</div>;
}
