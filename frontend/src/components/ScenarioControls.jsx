import { postureLabel } from "../domain/format.js";
import { EFFECT_EXAMPLES, GLOSSARY, LINE_TOOLTIP } from "../domain/glossary.js";
import { PRESETS, findPresetByHour } from "../domain/presets.js";
import InfoTooltip from "./InfoTooltip.jsx";

// Advanced ΔT mode tooltip (feedback round 2, point 16): rewritten to say what it does and
// when to use it, in neutral Spanish, with the real slider range (verified against
// src/gemetro/scenario.py SLIDERS["delta_t"]: min 0.0, max 18.0 — not the "+2 to +18" the
// direction assumed).
const ADVANCED_MODE_TOOLTIP =
  "Modo avanzado: en lugar de calcular la temperatura interior a partir del tiempo de " +
  "renovación de aire y los pasajeros, se fija directamente cuánto más caliente está el " +
  "interior que el exterior (de 0 a 18 °C, el rango de sensibilidad de Fase 0). Sirve para " +
  "explorar escenarios sin depender del supuesto de ventilación; el tiempo de renovación " +
  "equivalente se muestra solo como referencia. Es un supuesto del usuario.";

// Scenario presets (hour only), line selector (the same A | B segmented control guided mode
// uses, visual QA fix round 3 — no native white <select> for it), the habitual controls
// (hour, τr) shown immediately, and the collapsible advanced configuration (φ_pico, vel,
// clo, posture, and the ΔT advanced mode) for the less-frequently-touched parameters. No
// control sets N: the API-returned N is only shown in the result cards. No scientific
// parameter or allowed value is added or removed here — only where each control is shown.
export default function ScenarioControls({ config, scenario, isCustom, onPresetSelect, onFieldChange, onAdvancedToggle }) {
  const { sliders } = config;
  const selectedPreset = scenario.advanced ? null : findPresetByHour(scenario.hour);

  return (
    <section className="scenario-controls">
      <h3 className="controls-heading">Controles principales</h3>
      <div className="preset-row" role="group" aria-label="Escenarios predefinidos">
        {PRESETS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            className={`preset-button${selectedPreset?.id === preset.id ? " is-selected" : ""}`}
            aria-pressed={selectedPreset?.id === preset.id}
            onClick={() => onPresetSelect(preset.id)}
          >
            {preset.label}
          </button>
        ))}
      </div>

      <p className="field-label">Línea <InfoTooltip text={LINE_TOOLTIP} /></p>
      <div className="line-select" role="group" aria-label="Línea">
        {config.lines.map((line) => (
          <button
            key={line}
            type="button"
            className={`segmented-button${scenario.line === line ? " is-selected" : ""}`}
            aria-pressed={scenario.line === line}
            onClick={() => onFieldChange("line", line)}
          >
            {line}
          </button>
        ))}
      </div>

      {isCustom && <p className="custom-flag" role="status">Configuración personalizada</p>}

      {/* Habitual controls (visual QA fix round 3): hour and τr are touched often enough
          that hiding them behind "Configuración avanzada" cost an extra click every time. */}
      <div className="main-controls-grid">
        <label>
          <span>Hora del día</span>
          <input
            type="range"
            min={sliders.hour.min}
            max={sliders.hour.max}
            step={sliders.hour.step}
            value={scenario.hour}
            onChange={(event) => onFieldChange("hour", Number(event.target.value))}
          />
          <output>{scenario.hour} h</output>
        </label>

        <label>
          <span>
            Tiempo de renovación de aire{" "}
            <InfoTooltip text={`${GLOSSARY.tauR} ${EFFECT_EXAMPLES.tauR}`} />
          </span>
          <select
            value={scenario.tau_r}
            disabled={scenario.advanced}
            onChange={(event) => onFieldChange("tau_r", Number(event.target.value))}
          >
            {sliders.tau_r.values.map((value) => (
              <option key={value} value={value}>{value} s</option>
            ))}
          </select>
        </label>
      </div>

      <details className="advanced-config" data-testid="advanced-config">
        <summary>Configuración avanzada</summary>
        <div className="advanced-grid">
          <label>
            <span>
              Ocupación en hora pico{" "}
              <InfoTooltip text={`${GLOSSARY.phiPeak} ${EFFECT_EXAMPLES.phiPeak}`} />
            </span>
            <input
              type="range"
              min={sliders.phi_peak.min}
              max={sliders.phi_peak.max}
              step={sliders.phi_peak.step}
              value={scenario.phi_peak}
              onChange={(event) => onFieldChange("phi_peak", Number(event.target.value))}
            />
            <output>{scenario.phi_peak}</output>
          </label>

          <label>
            <span>
              Velocidad del aire <InfoTooltip text={`${GLOSSARY.vel} ${EFFECT_EXAMPLES.vel}`} />
            </span>
            <input
              type="range"
              min={sliders.vel.min}
              max={sliders.vel.max}
              step={sliders.vel.step}
              value={scenario.vel}
              onChange={(event) => onFieldChange("vel", Number(event.target.value))}
            />
            <output>{scenario.vel} m/s</output>
          </label>

          <label>
            <span>
              Aislamiento de la ropa <InfoTooltip text={`${GLOSSARY.clo} ${EFFECT_EXAMPLES.clo}`} />
            </span>
            <input
              type="range"
              min={sliders.clo.min}
              max={sliders.clo.max}
              step={sliders.clo.step}
              value={scenario.clo}
              onChange={(event) => onFieldChange("clo", Number(event.target.value))}
            />
            <output>{scenario.clo} clo</output>
          </label>

          <label>
            {/* The tooltip trigger stays after the <select> (not before, inside the same
                <span> as the label text): a label's implicit association picks the FIRST
                focusable descendant, and a leading tooltip button would shadow the <select>
                for getByLabelText/keyboard "click the label" behavior. */}
            <span>Postura</span>
            <span className="select-with-tip">
              <select
                value={scenario.posture}
                onChange={(event) => onFieldChange("posture", event.target.value)}
              >
                {config.postures.map((posture) => (
                  <option key={posture} value={posture}>{postureLabel(posture)}</option>
                ))}
              </select>
              <InfoTooltip text={EFFECT_EXAMPLES.posture} />
            </span>
          </label>

          <label className="advanced-toggle">
            <input
              type="checkbox"
              checked={scenario.advanced}
              onChange={(event) => onAdvancedToggle(event.target.checked)}
            />
            <span>
              Modo avanzado: fijar la diferencia de temperatura interior–exterior{" "}
              <InfoTooltip text={ADVANCED_MODE_TOOLTIP} />
            </span>
          </label>

          {scenario.advanced && (
            <label>
              <span>Diferencia fijada</span>
              <input
                type="range"
                min={sliders.delta_t.min}
                max={sliders.delta_t.max}
                step={sliders.delta_t.step}
                value={scenario.delta_t ?? sliders.delta_t.min}
                onChange={(event) => onFieldChange("delta_t", Number(event.target.value))}
              />
              <output>{scenario.delta_t} K</output>
            </label>
          )}
        </div>
      </details>
    </section>
  );
}
