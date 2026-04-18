import { afterEach, beforeAll } from "vitest";
import { cleanup } from "@testing-library/react";

function createMemoryStorage(): Storage {
  const state = new Map<string, string>();

  return {
    get length() {
      return state.size;
    },
    clear() {
      state.clear();
    },
    getItem(key: string) {
      return state.has(key) ? state.get(key)! : null;
    },
    key(index: number) {
      return Array.from(state.keys())[index] ?? null;
    },
    removeItem(key: string) {
      state.delete(key);
    },
    setItem(key: string, value: string) {
      state.set(key, String(value));
    },
  };
}

function hasUsableStorage(candidate: unknown): candidate is Storage {
  if (!candidate || typeof candidate !== "object") {
    return false;
  }

  const storage = candidate as Partial<Storage>;
  return (
    typeof storage.clear === "function"
    && typeof storage.getItem === "function"
    && typeof storage.key === "function"
    && typeof storage.removeItem === "function"
    && typeof storage.setItem === "function"
  );
}

function installStorage(name: "localStorage" | "sessionStorage") {
  const memoryStorage = createMemoryStorage();

  if (typeof window !== "undefined") {
    Object.defineProperty(window, name, {
      configurable: true,
      enumerable: true,
      writable: true,
      value: memoryStorage,
    });
  }

  Object.defineProperty(globalThis, name, {
    configurable: true,
    enumerable: true,
    writable: true,
    value: memoryStorage,
  });
}

function ensureBrowserStorage() {
  if (!hasUsableStorage(globalThis.localStorage)) {
    installStorage("localStorage");
  }

  if (!hasUsableStorage(globalThis.sessionStorage)) {
    installStorage("sessionStorage");
  }
}

beforeAll(() => {
  ensureBrowserStorage();

  if (typeof window !== "undefined" && typeof window.matchMedia !== "function") {
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      writable: true,
      value: (query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
        addListener: () => undefined,
        removeListener: () => undefined,
        dispatchEvent: () => false,
      }),
    });
  }

  if (typeof globalThis.ResizeObserver === "undefined") {
    class ResizeObserverMock {
      observe() {}
      unobserve() {}
      disconnect() {}
    }

    Object.defineProperty(globalThis, "ResizeObserver", {
      configurable: true,
      writable: true,
      value: ResizeObserverMock,
    });
  }

  if (typeof globalThis.IntersectionObserver === "undefined") {
    class IntersectionObserverMock {
      root = null;
      rootMargin = "";
      thresholds = [];

      observe() {}
      unobserve() {}
      disconnect() {}
      takeRecords() {
        return [];
      }
    }

    Object.defineProperty(globalThis, "IntersectionObserver", {
      configurable: true,
      writable: true,
      value: IntersectionObserverMock,
    });
  }
});

afterEach(() => {
  cleanup();
  globalThis.localStorage.clear();
  globalThis.sessionStorage.clear();

  if (typeof window !== "undefined") {
    window.location.hash = "";
  }
});
