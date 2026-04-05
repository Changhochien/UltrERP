/** Auth context – stores JWT, exposes user info and login/logout. */

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { AUTH_STORAGE_EVENT, clearStoredToken, getStoredToken, setStoredToken, TOKEN_KEY } from "../lib/authStorage";

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  return atob(padded);
}

export interface AuthUser {
  sub: string;
  role: string;
  tenant_id: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isAuthLoading: boolean;
  login: (email: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const DEV_AUTO_LOGIN_ENABLED = import.meta.env.DEV
  && import.meta.env.MODE !== "test"
  && import.meta.env.VITE_DEV_AUTO_LOGIN === "true";
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

let devAutoLoginPromise: Promise<{ ok: boolean; error?: string }> | null = null;

function isUuid(value: unknown): value is string {
  return typeof value === "string" && UUID_PATTERN.test(value);
}

function runDevAutoLogin(
  login: (email: string, password: string) => Promise<{ ok: boolean; error?: string }>,
) {
  devAutoLoginPromise ??= login("admin@ultr.dev", "admin123").finally(() => {
    devAutoLoginPromise = null;
  });

  return devAutoLoginPromise;
}

function decodePayload(token: string): AuthUser | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(decodeBase64Url(parts[1]));
    if (!isUuid(payload.sub) || typeof payload.role !== "string" || !isUuid(payload.tenant_id)) return null;
    // Check expiry
    if (payload.exp && payload.exp * 1000 < Date.now()) return null;
    return { sub: payload.sub, role: payload.role, tenant_id: payload.tenant_id };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    const stored = getStoredToken();
    if (!stored) return null;
    // Validate token is still usable
    if (!decodePayload(stored)) {
      clearStoredToken();
      return null;
    }
    return stored;
  });

  const user = useMemo(() => (token ? decodePayload(token) : null), [token]);
  const isAuthenticated = !!user;
  const [isAuthLoading, setIsAuthLoading] = useState(
    () => DEV_AUTO_LOGIN_ENABLED && !getStoredToken(),
  );

  useEffect(() => {
    function syncTokenFromStorage() {
      const stored = getStoredToken();
      if (!stored) {
        setToken(null);
        return;
      }
      if (!decodePayload(stored)) {
        clearStoredToken();
        setToken(null);
        return;
      }
      setToken(stored);
    }

    function handleStorage(event: StorageEvent) {
      if (event.key !== null && event.key !== TOKEN_KEY) {
        return;
      }
      syncTokenFromStorage();
    }

    window.addEventListener(AUTH_STORAGE_EVENT, syncTokenFromStorage);
    window.addEventListener("storage", handleStorage);
    return () => {
      window.removeEventListener(AUTH_STORAGE_EVENT, syncTokenFromStorage);
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  // Periodically check token expiry
  useEffect(() => {
    if (!token) return;
    const id = setInterval(() => {
      if (!decodePayload(token)) {
        clearStoredToken();
      }
    }, 60_000);
    return () => clearInterval(id);
  }, [token]);

  // Dev auto-login: bypass the login form when VITE_DEV_AUTO_LOGIN is set
  useEffect(() => {
    if (!DEV_AUTO_LOGIN_ENABLED) {
      setIsAuthLoading(false);
      return;
    }
    if (isAuthenticated) {
      setIsAuthLoading(false);
      return;
    }
    runDevAutoLogin(login).finally(() => setIsAuthLoading(false));
  }, []);

  async function login(email: string, password: string): Promise<{ ok: boolean; error?: string }> {
    let resp: Response;
    try {
      resp = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
    } catch {
      return { ok: false, error: "Unable to reach the server." };
    }

    if (!resp.ok) {
      return { ok: false, error: "Invalid credentials" };
    }

    const body = await resp.json();
    const accessToken: string = body.access_token;
    if (!decodePayload(accessToken)) {
      return { ok: false, error: "Invalid token received." };
    }
    setStoredToken(accessToken);
    setToken(accessToken);
    return { ok: true };
  }

  function logout() {
    clearStoredToken();
    setToken(null);
  }

  const value: AuthContextValue = useMemo(
    () => ({ user, token, isAuthenticated: !!user, isAuthLoading, login, logout }),
    [user, token, isAuthLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useOptionalAuth();
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function useOptionalAuth(): AuthContextValue | null {
  return useContext(AuthContext);
}
