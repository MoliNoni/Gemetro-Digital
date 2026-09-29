// Loading feedback: skeletons on first load only (never on refetch), and the header notice
// shown while /config loads (the Render-hosted API may be cold-starting).
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { CONFIG, GUIDED_ENTRY_IN_DOMAIN, RECORD, guidedResponse } from "./fixtures.js";

vi.mock("../src/api/client.js", () => ({
  fetchConfig: vi.fn(),
  runScenario: vi.fn(),
  runDayProfile: vi.fn(),
  fetchGuided: vi.fn(),
}));

import { fetchConfig, fetchGuided, runDayProfile, runScenario } from "../src/api/client.js";
import App from "../src/App.jsx";
import Header from "../src/components/Header.jsx";

const WAKEUP = /Cargando despliegue en Render/;

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.clearAllMocks();
  fetchConfig.mockResolvedValue(CONFIG);
  runScenario.mockImplementation((params) =>
    Promise.resolve({ ...RECORD, scenario: { ...RECORD.scenario, ...params } }));
  runDayProfile.mockResolvedValue([]);
  fetchGuided.mockImplementation((line, period) =>
    Promise.resolve(guidedResponse(line, period, [GUIDED_ENTRY_IN_DOMAIN])));
});

// See App.test.jsx: globals are off, so cleanup must be explicit.
afterEach(cleanup);

describe("header notice", () => {
  test("renders only while the API status is loading", () => {
    const { rerender } = render(<Header apiStatus="loading" />);
    expect(screen.getByRole("status")).toHaveTextContent(WAKEUP);
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");

    rerender(<Header apiStatus="result" />);
    expect(screen.queryByText(WAKEUP)).not.toBeInTheDocument();
  });
});

describe("initial config load", () => {
  test("shows the layout skeleton and the header notice, then removes both on result", async () => {
    const config = deferred();
    fetchConfig.mockReturnValue(config.promise);
    const { container } = render(<App />);

    expect(screen.getByText(WAKEUP)).toBeInTheDocument();
    expect(screen.getByText("Conectando con el servicio…")).toBeInTheDocument();
    expect(container.querySelector(".layout-grid[aria-busy='true']")).toBeInTheDocument();
    expect(container.querySelectorAll(".skeleton").length).toBeGreaterThan(0);

    config.resolve(CONFIG);
    await screen.findByRole("group", { name: "Modo del simulador" });
    expect(screen.queryByText(WAKEUP)).not.toBeInTheDocument();
    expect(screen.queryByText("Conectando con el servicio…")).not.toBeInTheDocument();
    expect(container.querySelector(".layout-grid[aria-busy='true']")).not.toBeInTheDocument();
  });

  test("removes the header notice and the skeleton when /config fails", async () => {
    fetchConfig.mockRejectedValue(new Error("boom"));
    const { container } = render(<App />);

    await waitFor(() => {
      expect(screen.queryByText(WAKEUP)).not.toBeInTheDocument();
    });
    expect(container.querySelector(".skeleton")).not.toBeInTheDocument();
  });
});

describe("guided mode", () => {
  test("shows skeletons on first load and keeps data (dimmed, no skeleton) on refetch", async () => {
    const first = deferred();
    fetchGuided.mockReturnValueOnce(first.promise);
    const { container } = render(<App />);

    await screen.findByRole("group", { name: "Modo del simulador" });
    expect(screen.getByText("Calculando…")).toBeInTheDocument();
    expect(container.querySelectorAll(".skeleton").length).toBeGreaterThan(0);
    expect(screen.queryByRole("group", { name: "Horas del periodo" })).not.toBeInTheDocument();

    first.resolve(guidedResponse("A", "afternoon", [GUIDED_ENTRY_IN_DOMAIN]));
    await screen.findByRole("group", { name: "Horas del periodo" });
    expect(container.querySelector(".skeleton")).not.toBeInTheDocument();

    const refetch = deferred();
    fetchGuided.mockReturnValueOnce(refetch.promise);
    await userEvent.setup().click(screen.getByRole("button", { name: "Noche" }));

    await waitFor(() => {
      expect(container.querySelector(".col-center.is-updating")).toBeInTheDocument();
    });
    expect(container.querySelector(".skeleton")).not.toBeInTheDocument();
  });
});

describe("simulation mode", () => {
  test("shows result skeletons on first load, then the real result", async () => {
    const scenario = deferred();
    runScenario.mockReturnValue(scenario.promise);
    const { container } = render(<App />);
    await screen.findByRole("group", { name: "Modo del simulador" });

    await userEvent.setup().click(screen.getByRole("button", { name: "Modo simulación" }));
    expect((await screen.findAllByText("Calculando…")).length).toBeGreaterThanOrEqual(1);
    expect(container.querySelector(".col-center .skeleton-wagon")).toBeInTheDocument();
    expect(container.querySelectorAll(".skeleton-chart").length).toBe(2);

    scenario.resolve(RECORD);
    await screen.findByText(/Confort según ML/i);
    expect(container.querySelector(".skeleton-wagon")).not.toBeInTheDocument();
  });

  test("shows a chart skeleton while the daily profile first loads", async () => {
    const profile = deferred();
    runDayProfile.mockReturnValue(profile.promise);
    const { container } = render(<App />);
    await screen.findByRole("group", { name: "Modo del simulador" });

    await userEvent.setup().click(screen.getByRole("button", { name: "Modo simulación" }));
    await screen.findByText(/Confort según ML/i);

    expect(screen.getByText("Calculando el perfil diario…")).toBeInTheDocument();
    expect(container.querySelector(".skeleton-chart")).toBeInTheDocument();
  });
});
