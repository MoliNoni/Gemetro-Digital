import "@testing-library/jest-dom/vitest";

// jsdom has no ResizeObserver; Recharts' <ResponsiveContainer> needs one to mount at all
// (it does not affect the assertions below, which read the status list/text, not pixel
// sizes).
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
