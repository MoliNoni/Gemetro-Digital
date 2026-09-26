// App-level tests: mode switch (guided is the default view), guided mode's default hour
// selection and "abrir en simulación", and simulation-mode states carried over from F-02
// (presets, line selector, advanced config, custom-configuration flag, tooltips, no
// confidence wording) — P-27 at component level.
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test } from "vitest";
import { vi } from "vitest";

import { CONFIG, GUIDED_ENTRY_FALLBACK, GUIDED_ENTRY_IN_DOMAIN, RECORD, guidedResponse } from "./fixtures.js";

vi.mock("../src/api/client.js", () => ({
  fetchConfig: vi.fn(),
  runScenario: vi.fn(),
  runDayProfile: vi.fn(),
  fetchGuided: vi.fn(),
}));

import { fetchConfig, fetchGuided, runDayProfile, runScenario } from "../src/api/client.js";
import App from "../src/App.jsx";

function recordFor(params) {
  return { ...RECORD, scenario: { ...RECORD.scenario, ...params } };
}

beforeEach(() => {
  vi.clearAllMocks();
  fetchConfig.mockResolvedValue(CONFIG);
  runScenario.mockImplementation((params) => Promise.resolve(recordFor(params)));
  runDayProfile.mockResolvedValue([]);
  fetchGuided.mockImplementation((line, period) =>
    Promise.resolve(guidedResponse(line, period, [GUIDED_ENTRY_FALLBACK, GUIDED_ENTRY_IN_DOMAIN])));
});

// vite.config.js sets test.globals: false, so Testing Library's auto-cleanup (which relies
// on a global `afterEach`) never registers; clean up explicitly instead, or each test would
// see every previous test's DOM still mounted.
afterEach(cleanup);

async function renderApp() {
  render(<App />);
  await screen.findByRole("group", { name: "Modo del simulador" });
}

async function switchToSimulation() {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Modo simulación" }));
  await screen.findByText(/Confort según ML/i);
  return user;
}

describe("mode switch", () => {
  test("guided mode is the default view", async () => {
    await renderApp();
    expect(screen.getByRole("button", { name: "Modo guiado" })).toHaveAttribute("aria-pressed", "true");
    await screen.findByRole("group", { name: "Horas del periodo" });
    expect(screen.queryByText("Configuración avanzada")).not.toBeInTheDocument();
  });

  test("switching to simulation mode shows the free-parameter controls", async () => {
    await renderApp();
    await switchToSimulation();
    expect(screen.getByText("Configuración avanzada")).toBeInTheDocument();
  });
});

describe("guided mode", () => {
  test("shows every hour's domain coverage and labels the hour without coverage", async () => {
    await renderApp();
    await screen.findByRole("group", { name: "Horas del periodo" });

    expect(screen.getByText("3/8")).toBeInTheDocument(); // GUIDED_ENTRY_FALLBACK.coverage
    expect(screen.getAllByText("Fuera del dominio").length).toBeGreaterThanOrEqual(1);
  });

  test("defaults to the highest-coverage hour (ties to the earliest)", async () => {
    await renderApp();
    await screen.findByRole("group", { name: "Horas del periodo" });

    // GUIDED_ENTRY_IN_DOMAIN (16 h, coverage 3/8) beats GUIDED_ENTRY_FALLBACK (12 h, 0/8).
    expect(screen.getByRole("button", { name: /16 h/ })).toHaveAttribute("aria-pressed", "true");
  });

  test("an hour without coverage is labeled and not shown as a normal prediction", async () => {
    await renderApp();
    await screen.findByRole("group", { name: "Horas del periodo" });
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /12 h/ }));

    // No permanent literal banner (visual QA fix): the hour chip's own tiny status label and
    // the ML card's status pill both read "Fuera del dominio" — an explanatory tooltip lives
    // on the pill itself, not a separate always-visible sentence.
    await waitFor(() => {
      expect(screen.getAllByText("Fuera del dominio").length).toBeGreaterThanOrEqual(2);
    });
    expect(screen.queryByText(/está fuera del rango de los datos de Nanjing/)).not.toBeInTheDocument();
  });

});

describe("simulation mode: default scenario", () => {
  test("renders ML/PMV domain and range states, each with a compact directional tooltip on its own pill", async () => {
    await renderApp();
    await switchToSimulation();

    expect(screen.getAllByText("Fuera del dominio").length).toBeGreaterThanOrEqual(1); // RECORD.ml is ML_OUT
    expect(screen.getAllByText(RECORD.pmv.status).length).toBeGreaterThanOrEqual(1);
    // Compact directional inequality vs the /config bound (visual QA fix), Spanish decimal
    // comma, no permanent literal sentence anywhere in the results.
    expect(screen.getByText(/RH \d+ % < 52,05 %/)).toBeInTheDocument(); // ML: rh_in (45 %) < domain.rh.min
    expect(screen.getByText(/Ta \d+,\d °C > 30,00 °C/)).toBeInTheDocument(); // PMV: tin_c (31,5 °C) > pmv_ranges.ta.max
  });

  test("a user-forced out-of-domain scenario has no permanent banner: the ML pill itself is the tooltip trigger", async () => {
    await renderApp();
    await switchToSimulation();

    expect(screen.queryByText("Escenario fuera de dominio")).not.toBeInTheDocument();
    expect(screen.queryByText(/está fuera del rango de los datos de Nanjing/)).not.toBeInTheDocument();

    const mlPill = screen.getByText("Fuera del dominio").closest("button");
    expect(mlPill).toBeInTheDocument();
    expect(mlPill).toHaveAttribute("aria-label", "Por qué está fuera del dominio");
  });

  test("shows provenance as received, unchanged, for every card", async () => {
    await renderApp();
    await switchToSimulation();

    // record.provenance.tin and .rh_in are both "Simulado" in this fixture: both rows show it.
    expect(screen.getAllByText(RECORD.provenance.tin).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(RECORD.provenance.n)).toBeInTheDocument();
    expect(screen.getByText(RECORD.provenance.ml_class)).toBeInTheDocument();
    // The PMV card's own provenance tooltip is removed (feedback round 2, point 4: it only
    // ever showed "Asignación normativa", which added no information next to a card whose
    // own status already reads as normative); no assertion for it here anymore.
  });
});

test("clicking a preset changes the hour sent to the API without a page reload", async () => {
  await renderApp();
  await switchToSimulation();
  runScenario.mockClear();
  const user = userEvent.setup();

  await user.click(screen.getByRole("button", { name: "Madrugada" }));

  await waitFor(() => {
    expect(runScenario).toHaveBeenCalledWith(
      expect.objectContaining({ hour: 5, line: "A" }),
      expect.anything(),
    );
  });
  // No navigation/reload: the same App instance is still mounted with its header. The
  // wordmark's accessible name stays "Gemetro Digital" even though it is now split across
  // two <span> elements (feedback round 2, point 14), so this is an accessible-name query
  // (getByRole), not a direct-text-node query (getByText would not see across elements).
  expect(screen.getByRole("heading", { name: "Gemetro Digital" })).toBeInTheDocument();
});

test("the line selector (A | B segmented control, same as guided mode) sends the chosen line", async () => {
  await renderApp();
  await switchToSimulation();
  runScenario.mockClear();
  const user = userEvent.setup();

  await user.click(within(screen.getByRole("group", { name: "Línea" })).getByRole("button", { name: "B" }));

  await waitFor(() => {
    expect(runScenario).toHaveBeenCalledWith(expect.objectContaining({ line: "B" }), expect.anything());
  });
});

test("the previous result stays visible and dimmed, with a visible loading indicator, while a new one loads", async () => {
  await renderApp();
  await switchToSimulation();

  // Sanity: the default result is already showing before triggering an update.
  expect(screen.getAllByText(RECORD.pmv.status).length).toBeGreaterThanOrEqual(1);
  expect(document.querySelector(".col-center.is-updating")).not.toBeInTheDocument();

  // A deferred mock (visual QA fix round 3): runScenario's promise is only resolved once we
  // call `resolveNext`, so the test can observe the in-between "updating" state instead of
  // racing a promise that resolves on the same microtask.
  let resolveNext;
  const deferred = new Promise((resolve) => {
    resolveNext = resolve;
  });
  runScenario.mockImplementation(() => deferred);

  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Madrugada" }));

  await waitFor(() => {
    expect(document.querySelector(".col-center.is-updating")).toBeInTheDocument();
  });
  // Never unmounted/blank: the previous result's own content is still rendered underneath.
  expect(screen.getAllByText(RECORD.pmv.status).length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText("Actualizando…")).toBeInTheDocument();

  resolveNext(recordFor({ hour: 5 }));
  await waitFor(() => {
    expect(document.querySelector(".col-center.is-updating")).not.toBeInTheDocument();
  });
});

test("advanced config is collapsed by default and expands on click", async () => {
  await renderApp();
  await switchToSimulation();
  const details = screen.getByTestId("advanced-config");
  expect(details).not.toHaveAttribute("open");

  const user = userEvent.setup();
  await user.click(screen.getByText("Configuración avanzada"));

  expect(details).toHaveAttribute("open");
});

test("the custom-configuration flag appears only once a non-hour value changes", async () => {
  await renderApp();
  await switchToSimulation();
  expect(screen.queryByText("Configuración personalizada")).not.toBeInTheDocument();

  const user = userEvent.setup();
  await user.click(screen.getByText("Configuración avanzada"));
  await user.selectOptions(screen.getByLabelText(/Postura/), "standing");

  expect(screen.getByText("Configuración personalizada")).toBeInTheDocument();
});

test("tooltips appear on hover and on keyboard focus, and hide again", async () => {
  await renderApp();
  await switchToSimulation();
  const user = userEvent.setup();
  // Picks a trigger that is not inside the collapsed "Configuración avanzada" <details> (its
  // content is not visible until expanded); the ML card's tooltip always renders open.
  const trigger = screen
    .getAllByRole("button", { name: "Más información" })
    .find((button) => button.closest("details") === null);
  const tooltip = document.getElementById(trigger.getAttribute("aria-describedby"));

  expect(tooltip).not.toBeVisible();

  await user.hover(trigger);
  expect(tooltip).toBeVisible();
  await user.unhover(trigger);
  expect(tooltip).not.toBeVisible();

  fireEvent.focus(trigger);
  expect(tooltip).toBeVisible();
  fireEvent.blur(trigger);
  expect(tooltip).not.toBeVisible();
});

test("no confidence, probability, accuracy or F1 wording appears anywhere in the rendered app", async () => {
  await renderApp();
  await screen.findByRole("group", { name: "Horas del periodo" }); // guided (default) view
  await switchToSimulation();
  const text = document.body.textContent;
  expect(text).not.toMatch(/confianza|probabilidad|accuracy|f1|precisión estimada/i);
});
