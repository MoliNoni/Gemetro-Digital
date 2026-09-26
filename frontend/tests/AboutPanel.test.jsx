import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import AboutPanel from "../src/components/AboutPanel.jsx";

afterEach(cleanup);

describe("AboutPanel", () => {
  test("is closed by default and opens when `open` is true (floating, non-blocking panel)", () => {
    const { rerender } = render(<AboutPanel open={false} onToggle={() => {}} />);
    expect(screen.getByRole("button", { name: "¿Qué estoy viendo?" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    rerender(<AboutPanel open onToggle={() => {}} />);
    expect(screen.getByRole("dialog", { name: "¿Qué estoy viendo?" })).toBeInTheDocument();
  });

  test("explains the three panels and the project context (direction 2026-09-26)", () => {
    render(<AboutPanel open onToggle={() => {}} />);
    expect(document.querySelectorAll(".about-panels dt").length).toBe(3);
    expect(screen.getByText(/Izquierda/)).toBeInTheDocument();
    expect(screen.getByText(/Centro/)).toBeInTheDocument();
    expect(screen.getByText(/Derecha/)).toBeInTheDocument();

    expect(screen.getByText(/pseudo digital twin/)).toBeInTheDocument();
    expect(screen.getByText(/tiempo real/i)).toBeInTheDocument();
    expect(screen.getByText(/validación empírica/)).toBeInTheDocument();
    expect(screen.getByText(/encuestas reales del metro de Nanjing/)).toBeInTheDocument();
    expect(screen.getByText(/"Fuera del dominio"/)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "repositorio" })[0]).toHaveAttribute("href", "https://github.com/MoliNoni");
  });

  test("no confidence, probability or accuracy figure is shown", () => {
    render(<AboutPanel open onToggle={() => {}} />);
    const text = document.body.textContent.toLowerCase();
    for (const word of ["confianza", "probabilidad", "precisión estimada", "accuracy"]) {
      expect(text.includes(word)).toBe(false);
    }
  });

  test("clicking the floating button toggles open, and the close button closes it", () => {
    const onToggle = vi.fn();
    const { rerender } = render(<AboutPanel open={false} onToggle={onToggle} />);
    screen.getByRole("button", { name: "¿Qué estoy viendo?" }).click();
    expect(onToggle).toHaveBeenCalledWith(true);

    onToggle.mockClear();
    rerender(<AboutPanel open onToggle={onToggle} />);
    screen.getByRole("button", { name: "Cerrar" }).click();
    expect(onToggle).toHaveBeenCalledWith(false);
  });

  test("is not a blocking modal: it renders no full-page backdrop", () => {
    render(<AboutPanel open onToggle={() => {}} />);
    expect(document.querySelector(".modal-backdrop, .overlay")).not.toBeInTheDocument();
  });
});
