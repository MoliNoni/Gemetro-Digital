// G-02: a 503 (model not loaded) always reads "Modelo no disponible"; anything else shows
// the message as received. Both keep the "error" (red) style, never "warn" — this is a real
// failure, not an extrapolation/out-of-range state.
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import ApiErrorNotice from "../src/components/ApiErrorNotice.jsx";

afterEach(cleanup);

describe("ApiErrorNotice", () => {
  test('a 503 reads "Modelo no disponible", not the raw detail text', () => {
    render(<ApiErrorNotice error="model not loaded" httpStatus={503} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Modelo no disponible");
    expect(screen.getByRole("alert").className).toBe("error");
  });

  test("any other error shows its message", () => {
    render(<ApiErrorNotice error="Failed to fetch" httpStatus={null} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Error: Failed to fetch");
  });

  test("shows a retry button only when onRetry is given", () => {
    const onRetry = vi.fn();
    const { rerender } = render(<ApiErrorNotice error="x" httpStatus={null} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();

    rerender(<ApiErrorNotice error="x" httpStatus={null} onRetry={onRetry} />);
    screen.getByRole("button", { name: "Reintentar" }).click();
    expect(onRetry).toHaveBeenCalled();
  });
});
