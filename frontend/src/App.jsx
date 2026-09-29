import { useEffect, useMemo, useState } from "react";

import AboutPanel from "./components/AboutPanel.jsx";
import GuidedMode from "./components/GuidedMode.jsx";
import Footer from "./components/Footer.jsx";
import Header from "./components/Header.jsx";
import ModeSwitch from "./components/ModeSwitch.jsx";
import SimulationMode from "./components/SimulationMode.jsx";
import ApiErrorNotice from "./components/ApiErrorNotice.jsx";
import { AppSkeleton } from "./components/LoadingSkeletons.jsx";
import { roundHalf } from "./domain/format.js";
import { findPresetById, isCustomConfiguration, toScenarioParams } from "./domain/presets.js";
import { useConfig } from "./hooks/useConfig.js";
import { useDayProfile } from "./hooks/useDayProfile.js";
import { useGuidedSelection } from "./hooks/useGuidedSelection.js";
import { useScenario } from "./hooks/useScenario.js";

// G-01: guided mode is the default view; simulation mode is the previous free-parameter
// simulator. Scenario (simulation) state stays here, not inside SimulationMode, so
// switching back and forth between modes does not lose the user's simulation edits and
// does not refetch anything that has not actually changed — useScenario/useDayProfile only
// re-request when their parameters change, not when the mode toggles. The daily profile
// (19 requests) is only ever requested once simulation mode is actually shown (dayProfile's
// `nonHourParams` is null otherwise), so landing on guided mode never triggers it.
export default function App() {
  const { status: configStatus, config, error: configError, httpStatus: configHttpStatus, refetch: refetchConfig } =
    useConfig();
  const [mode, setMode] = useState("guided");
  const [aboutOpen, setAboutOpen] = useState(false);
  const guidedSelection = useGuidedSelection(config);
  const [scenario, setScenario] = useState(null);
  const [lastNormalDeltaT, setLastNormalDeltaT] = useState(null);

  useEffect(() => {
    if (config && scenario === null) {
      setScenario({ ...config.defaults, advanced: false, delta_t: null });
    }
  }, [config, scenario]);

  const scenarioParams = useMemo(
    () => (scenario ? toScenarioParams(scenario) : null),
    [scenario],
  );
  const scenarioState = useScenario(scenarioParams);

  const nonHourParams = useMemo(() => {
    if (mode !== "simulation" || !scenarioParams) return null;
    const { hour, ...rest } = scenarioParams;
    return rest;
  }, [mode, scenarioParams]);
  const dayProfileState = useDayProfile(nonHourParams, config);

  useEffect(() => {
    const record = scenarioState.result;
    if (record && record.scenario.mode === "normal") {
      setLastNormalDeltaT(record.indoor.delta_t);
    }
  }, [scenarioState.result]);

  function updateField(key, value) {
    setScenario((prev) => ({ ...prev, [key]: value }));
  }

  function selectPreset(id) {
    const preset = findPresetById(id);
    if (!preset || !config) return;
    setScenario({ ...config.defaults, hour: preset.hour, advanced: false, delta_t: null });
  }

  // Seeds ΔT from the last normal-mode result (clamped to the slider range) when advanced
  // mode is switched on, same behavior as the previous static frontend.
  function toggleAdvanced(checked) {
    setScenario((prev) => {
      if (!checked) return { ...prev, advanced: false, delta_t: null };
      const spec = config.sliders.delta_t;
      const seed = lastNormalDeltaT != null
        ? Math.min(spec.max, Math.max(spec.min, roundHalf(lastNormalDeltaT)))
        : spec.min;
      return { ...prev, advanced: true, delta_t: seed };
    });
  }

  const isCustom = config && scenario ? isCustomConfiguration(scenario, config.defaults) : false;

  return (
    <div className="app-shell">
      <Header apiStatus={configStatus} />
      {/* Feedback round 2 (direction 2026-09-25): "¿Qué estoy viendo?" moves back out of the
          header into a compact floating bubble, fixed bottom-right, so it never competes
          with the header's fixed budget and stays reachable while scrolling. */}
      <AboutPanel open={aboutOpen} onToggle={setAboutOpen} />

      {configStatus === "loading" && <AppSkeleton />}
      {configStatus === "error" && (
        <ApiErrorNotice error={configError} httpStatus={configHttpStatus} onRetry={refetchConfig} />
      )}

      {config && scenario && (
        <div className="layout-grid">
          <div className="col-left mode-switch-slot">
            <ModeSwitch mode={mode} onChange={setMode} />
          </div>
          {mode === "guided" ? (
            <GuidedMode config={config} selection={guidedSelection} />
          ) : (
            <SimulationMode
              config={config}
              scenario={scenario}
              isCustom={isCustom}
              scenarioState={scenarioState}
              dayProfileState={dayProfileState}
              onFieldChange={updateField}
              onPresetSelect={selectPreset}
              onAdvancedToggle={toggleAdvanced}
            />
          )}
        </div>
      )}

      <Footer />
    </div>
  );
}
