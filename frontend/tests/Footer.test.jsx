import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import Footer from "../src/components/Footer.jsx";
import { SOURCE_GROUPS } from "../src/domain/sources.js";

afterEach(cleanup);

describe("Footer", () => {
  test("lists every source group and item, and links the repository", () => {
    render(<Footer />);
    for (const group of SOURCE_GROUPS) {
      expect(screen.getByRole("heading", { name: group.title })).toBeInTheDocument();
      for (const item of group.items) {
        expect(screen.getByText(item.text)).toBeInTheDocument();
      }
    }
    expect(screen.getByRole("link", { name: "github.com/MoliNoni" })).toHaveAttribute(
      "href",
      "https://github.com/MoliNoni",
    );
  });

  test("names the ML training data and the Medellín scenario sources", () => {
    render(<Footer />);
    expect(screen.getByText(/metro de Nanjing/)).toBeInTheDocument();
    expect(screen.getByText(/IDEAM, estación Olaya Herrera/)).toBeInTheDocument();
    expect(screen.getByText(/afluencia 2025 y GTFS 2025/)).toBeInTheDocument();
  });
});
