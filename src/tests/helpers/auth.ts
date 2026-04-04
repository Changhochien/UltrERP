/** Sets a fake JWT in localStorage so AuthProvider sees an authenticated user. */

import { clearStoredToken, setStoredToken } from "../../lib/authStorage";

export function setTestToken(role = "owner") {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = btoa(
    JSON.stringify({
      sub: "test-user-id",
      role,
      tenant_id: "test-tenant",
      exp: Math.floor(Date.now() / 1000) + 3600,
    }),
  );
  const sig = btoa("fakesig");
  const token = `${header}.${payload}.${sig}`;
  setStoredToken(token);
  return token;
}

export function clearTestToken() {
  clearStoredToken();
}
