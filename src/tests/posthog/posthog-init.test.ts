import { describe, expect, it, vi, beforeEach } from "vitest";
import posthog from "posthog-js";

vi.mock("posthog-js", () => ({
  default: { init: vi.fn(), __loaded: false },
}));

describe("initPostHog", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
  });

  it("does not initialize when env vars are missing", async () => {
    vi.stubEnv("VITE_POSTHOG_KEY", "");
    vi.stubEnv("VITE_POSTHOG_HOST", "");

    const { initPostHog } = await import("../../lib/posthog");
    initPostHog();

    expect(posthog.init).not.toHaveBeenCalled();

    vi.unstubAllEnvs();
  });

  it("initializes with correct config when env vars are set", async () => {
    vi.stubEnv("VITE_POSTHOG_KEY", "phc_testkey");
    vi.stubEnv("VITE_POSTHOG_HOST", "https://ph.test.com");

    // Re-import to pick up new env values
    vi.resetModules();
    const ph = await import("posthog-js");
    ph.default.init = vi.fn();

    const mod = await import("../../lib/posthog");
    mod.initPostHog();

    expect(ph.default.init).toHaveBeenCalledWith(
      "phc_testkey",
      expect.objectContaining({
        api_host: "https://ph.test.com",
        person_profiles: "identified_only",
        capture_pageview: false,
        autocapture: true,
        disable_session_recording: true,
      }),
    );

    vi.unstubAllEnvs();
  });
});
