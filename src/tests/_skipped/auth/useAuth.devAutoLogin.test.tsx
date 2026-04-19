import { StrictMode } from "react";

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";


function encodeTokenPart(value: object): string {
  return btoa(JSON.stringify(value))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}


function makeAccessToken() {
  return [
    encodeTokenPart({ alg: "HS256", typ: "JWT" }),
    encodeTokenPart({
      sub: "admin@ultr.dev",
      role: "owner",
      tenant_id: "00000000-0000-0000-0000-000000000001",
      exp: Math.floor(Date.now() / 1000) + 3600,
    }),
    "signature",
  ].join(".");
}


afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  vi.resetModules();
});


describe("AuthProvider dev auto-login", () => {
  it("deduplicates the auto-login request under StrictMode", async () => {
    vi.stubEnv("DEV", true);
    vi.stubEnv("MODE", "development");
    vi.stubEnv("VITE_DEV_AUTO_LOGIN", "true");

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: makeAccessToken() }),
    } as Response);

    const { AuthProvider, useAuth } = await import("../../hooks/useAuth");

    function AuthProbe() {
      const { isAuthLoading, user } = useAuth();

      return <div>{isAuthLoading ? "loading" : (user?.sub ?? "guest")}</div>;
    }

    render(
      <StrictMode>
        <AuthProvider>
          <AuthProbe />
        </AuthProvider>
      </StrictMode>,
    );

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(screen.getByText("admin@ultr.dev")).toBeTruthy();
    });
  });
});