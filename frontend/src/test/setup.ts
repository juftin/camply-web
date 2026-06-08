import "@testing-library/jest-dom";

// jsdom in some environments has opaque origins where localStorage/sessionStorage
// throws. Provide a mock so DismissibleBanner and similar tests work.
if (typeof localStorage === "undefined" || localStorage === null) {
  const store: Record<string, string> = {};
  Object.defineProperty(globalThis, "localStorage", {
    value: {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => {
        store[key] = value;
      },
      removeItem: (key: string) => {
        delete store[key];
      },
      clear: () => {
        for (const k in store) delete store[k];
      },
    },
    writable: true,
  });
}
if (typeof sessionStorage === "undefined" || sessionStorage === null) {
  const store: Record<string, string> = {};
  Object.defineProperty(globalThis, "sessionStorage", {
    value: {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => {
        store[key] = value;
      },
      removeItem: (key: string) => {
        delete store[key];
      },
      clear: () => {
        for (const k in store) delete store[k];
      },
    },
    writable: true,
  });
}
