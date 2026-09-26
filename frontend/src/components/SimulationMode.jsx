import MetroCarVisualization from "./MetroCarVisualization.jsx";
import WagonIndicators from "./WagonIndicators.jsx";
import ResultCards from "./ResultCards.jsx";
import ConditionsPanel from "./ConditionsPanel.jsx";
import ScenarioControls from "./ScenarioControls.jsx";
import SensitivityChart from "./SensitivityChart.jsx";
import DailyProfileChart from "./DailyProfileChart.jsx";
import ApiErrorNotice from "./ApiErrorNotice.jsx";
// Simulation mode (the previous free-parameter simulator, G-02/G-03; three-column visual
// redesign): controls live in the left column, the wagon + central results + grouped
// conditions in the center column, and the charts in the right column. Scenario/day-profile
// state and their API calls live in App (so they are not refetched every time the user
// toggles back to guided mode and returns); this component only presents them. A
// user-forced out-of-domain scenario (GUIDED_MODE.md §3.4) is never a permanent banner: its
// ML card already reads "Fuera del dominio" with the reasons in its own hover tooltip
// (visual QA fix). While a new result loads (`dimmed`), the previous result stays mounted
// and dimmed and a small loading indicator appears next to it — never a blank/flickering
// screen.
export default function SimulationMode({
  config,
  scenario,
  isCustom,
  scenarioState,
  dayProfileState,
  onFieldChange,
  onPresetSelect,
  onAdvancedToggle,
}) {
  const record = scenarioState.result;
  const dimmed = scenarioState.status === "updating";

  return (
    <>
      <div className="col-left">
        <ScenarioControls
          config={config}
          scenario={scenario}
          isCustom={isCustom}
          onPresetSelect={onPresetSelect}
          onFieldChange={onFieldChange}
          onAdvancedToggle={onAdvancedToggle}
        />
      </div>

      {/* One col-center wrapper at most (feedback round 5): the grid makes the center and
          right columns span the mode-switch row, so two sibling col-center blocks would
          overlap instead of stacking. */}
      {!record && (scenarioState.status === "loading" || scenarioState.error) && (
        <div className="col-center">
          {scenarioState.status === "loading" && <p role="status">Calculando…</p>}
          {scenarioState.error && (
            <ApiErrorNotice
              error={scenarioState.error}
              httpStatus={scenarioState.httpStatus}
              onRetry={scenarioState.retry}
            />
          )}
        </div>
      )}

      {record && (
        <>
          <div className={`col-center${dimmed ? " is-updating" : ""}`} aria-busy={dimmed}>
            {dimmed && <p className="loading-indicator" role="status">Actualizando…</p>}
            {scenarioState.error && (
              <ApiErrorNotice
                error={scenarioState.error}
                httpStatus={scenarioState.httpStatus}
                onRetry={scenarioState.retry}
              />
            )}
            <div className="wagon-block">
              <MetroCarVisualization line={scenario.line} hour={scenario.hour} n={record.occupancy?.n} />
              <WagonIndicators record={record} />
            </div>

            <ResultCards record={record} dimmed={dimmed} domain={config.domain} pmvRanges={config.pmv_ranges} />
            <ConditionsPanel record={record} dimmed={dimmed} />
          </div>

          <div className="col-right">
            <SensitivityChart record={record} pragueReferenceS={config.prague_tau_reference_s} />

            {dayProfileState.status === "loading" && !dayProfileState.points && (
              <p role="status">Calculando el perfil diario…</p>
            )}
            {dayProfileState.error && (
              <ApiErrorNotice
                error={dayProfileState.error}
                httpStatus={dayProfileState.httpStatus}
                onRetry={dayProfileState.retry}
              />
            )}
            {dayProfileState.points && (
              <DailyProfileChart points={dayProfileState.points} selectedHour={scenario.hour} />
            )}
          </div>
        </>
      )}
    </>
  );
}
