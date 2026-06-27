// Minimal polyfills and test setup for Vitest + jsdom
// Provide IntersectionObserver for components that use it.
class DummyIntersectionObserver {
  callback: IntersectionObserverCallback;
  constructor(cb: IntersectionObserverCallback) {
    this.callback = cb;
  }
  observe() {
    // No-op; tests can manually call callback if needed
  }
  unobserve() {
    // No-op
  }
  disconnect() {
    // No-op
  }
  takeRecords() {
    return [];
  }
}

// Attach to global
(globalThis as any).IntersectionObserver = (globalThis as any).IntersectionObserver || DummyIntersectionObserver;

// Optional: provide matchMedia stub used by some UI libs
;(globalThis as any).matchMedia = (globalThis as any).matchMedia || function() {
  return {
    matches: false,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  };
};
