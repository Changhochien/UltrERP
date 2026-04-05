/** Sets a fake JWT in localStorage so AuthProvider sees an authenticated user. */

import { clearStoredToken, setStoredToken } from "../../lib/authStorage";

const DEFAULT_SUB = "00000000-0000-4000-8000-000000000001";
const DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001";

function encodeToken(payload: Record<string, unknown>) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  const sig = btoa("fakesig");
  return `${header}.${body}.${sig}`;
}

export function setTestToken(role = "owner") {
  const token = encodeToken({
    sub: DEFAULT_SUB,
    role,
    tenant_id: DEFAULT_TENANT_ID,
    exp: Math.floor(Date.now() / 1000) + 3600,
  });
  setStoredToken(token);
  return token;
}

export function setMalformedTestToken(role = "owner") {
  const token = encodeToken({
    sub: "test-user-id",
    role,
    tenant_id: "test-tenant",
    exp: Math.floor(Date.now() / 1000) + 3600,
  });
  setStoredToken(token);
  return token;
}

export function clearTestToken() {
  clearStoredToken();
}
