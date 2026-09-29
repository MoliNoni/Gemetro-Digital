import { GUIDED_PERIOD_ORDER as PERIOD_ORDER } from "../hooks/useGuidedSelection.js";
import { entryByHour } from "../domain/guidedSelection.js";
import ResultCards from "./ResultCards.jsx";
import ConditionsPanel from "./ConditionsPanel.jsx";
import MetroCarVisualization from "./MetroCarVisualization.jsx";
import WagonIndicators from "./WagonIndicators.jsx";
import SensitivityChart from "./SensitivityChart.jsx";
import { ChartsColumnSkeleton, HourStripSkeleton, ResultsColumnSkeleton } from "./LoadingSkeletons.jsx";
import ApiErrorNotice from "./ApiErrorNotice.jsx";
import InfoTooltip from "./InfoTooltip.jsx";
import { LINE_TOOLTIP } from "../domain/glossary.js";

const PERIOD_LABELS = { morning: "Mañana", midday: "Mediodía", afternoon: "Tarde", night: "Noche" };
const SELECTED_FALLBACK = "no_in_domain_fallback";

// Guided mode (G-01, GUIDED_MODE.md; three-column visual redesign): line + period
// selection and the hour strip live in the left column; the wagon, the ML/PMV/comparison
// block and the grouped conditions live in the center column (the page's greatest visual
// weight); the τr sensitivity chart/table lives in the right column. The default period is
// the one containing the closed default scenario's hour (line A, 16 h -> "afternoon"), so
// landing on guided mode reproduces the same scenario CA-10 already fixes as the default;
// this default-period choice was not specified by GUIDED_MODE.md §5 and is reversible.
// Feedback round 2 (direction 2026-09-25): "Abrir en simulación" removed (feature dropped by
// direction) — guided mode is now read-only with respect to the simulation scenario.
// ConditionsPanel gets `fixedParams` so its Operación group reads "Fijos en el modo guiado"
// instead of the simulation-mode row layout (vel/clo/posture are not editable here).
// Feedback round 5: selection state and the /guided result are owned by App
// (useGuidedSelection) and passed in as `selection`, so switching modes never empties this
// view or refetches.
export default function GuidedMode({ config, selection }) {
  const {
    line, setLine, period, setPeriod, selectedHour, setSelectedHour,
    status, data, error, httpStatus, retry,
  } = selection;

  const entry = data ? entryByHour(data.entries, selectedHour) : null;
  const dimmed = status === "updating";
  // Skeletons only on the first load; a refetch keeps the previous data dimmed instead.
  const loadingFirst = status === "loading" && !data;

  return (
    <>
      <div className="col-left guided-controls">
        <p className="field-label">Línea <InfoTooltip text={LINE_TOOLTIP} /></p>
        <div className="line-select" role="group" aria-label="Línea">
          {config.lines.map((l) => (
            <button
              key={l}
              type="button"
              className={`segmented-button${line === l ? " is-selected" : ""}`}
              aria-pressed={line === l}
              onClick={() => setLine(l)}
            >
              {l}
            </button>
          ))}
        </div>

        <p className="field-label">Periodo</p>
        <div className="period-row" role="group" aria-label="Periodo del día">
          {PERIOD_ORDER.map((name) => (
            <button
              key={name}
              type="button"
              className={`period-button${period === name ? " is-selected" : ""}`}
              aria-pressed={period === name}
              onClick={() => setPeriod(name)}
            >
              {PERIOD_LABELS[name]}
            </button>
          ))}
        </div>

        {data && (
          <>
            <p className="field-label">Horas</p>
            <div className="hour-strip" role="group" aria-label="Horas del periodo">
              {data.entries.map((e) => (
                <button
                  key={e.hour}
                  type="button"
                  className={
                    `hour-chip${e.hour === selectedHour ? " is-selected" : ""}` +
                    `${e.selection === SELECTED_FALLBACK ? " is-out-of-domain" : ""}`
                  }
                  aria-pressed={e.hour === selectedHour}
                  onClick={() => setSelectedHour(e.hour)}
                >
                  <span className="hour-chip-hour">{e.hour} h</span>
                  <span className="hour-chip-coverage">
                    {e.coverage.in_domain}/{e.coverage.total}
                  </span>
                  {/* Covered hours need no extra text (the spec only requires a state label
                      when there is no domain coverage at all); an uncovered hour reads as a
                      calm, tiny two-line amber label, never a red app-error state. */}
                  {e.selection === SELECTED_FALLBACK && (
                    <span className="hour-chip-status">Fuera del dominio</span>
                  )}
                </button>
              ))}
            </div>
          </>
        )}

        {loadingFirst && (
          <>
            <p className="field-label">Horas</p>
            <HourStripSkeleton />
          </>
        )}
        {error && <ApiErrorNotice error={error} httpStatus={httpStatus} onRetry={retry} />}
      </div>

      {loadingFirst && (
        <>
          <ResultsColumnSkeleton label="Calculando…" />
          <ChartsColumnSkeleton />
        </>
      )}

      {data && entry && (
        <>
          <div className={`col-center${dimmed ? " is-updating" : ""}`} aria-busy={dimmed}>
            <div className="wagon-block">
              <MetroCarVisualization line={line} hour={entry.hour} n={entry.record.occupancy?.n} />
              <WagonIndicators record={entry.record} />
            </div>

            <ResultCards
              record={entry.record}
              dimmed={dimmed}
              domain={config.domain}
              pmvRanges={config.pmv_ranges}
            />
            <ConditionsPanel record={entry.record} dimmed={dimmed} fixedParams />
          </div>

          <div className="col-right">
            <SensitivityChart record={entry.record} pragueReferenceS={config.prague_tau_reference_s} />
          </div>
        </>
      )}
    </>
  );
}
