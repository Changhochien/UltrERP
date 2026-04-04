/** Authenticated fetch wrapper – adds Bearer token, handles 401 redirects. */

import { clearStoredToken, getStoredToken } from "./authStorage";

export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const token = getStoredToken();
  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const resp = await fetch(input, { ...init, headers });

  if (resp.status === 401 && token) {
    // Token expired or invalid — clear and redirect to login
    clearStoredToken();
    window.location.hash = "#/login";
  }

  return resp;
}
