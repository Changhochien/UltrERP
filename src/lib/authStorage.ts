export const TOKEN_KEY = "ultrerp_token";
export const AUTH_STORAGE_EVENT = "ultrerp:auth-storage";

function emitAuthStorageChange() {
  window.dispatchEvent(new Event(AUTH_STORAGE_EVENT));
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
  emitAuthStorageChange();
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_KEY);
  emitAuthStorageChange();
}