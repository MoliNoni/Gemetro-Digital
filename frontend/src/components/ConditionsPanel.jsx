import {
  formatPercent,
  formatTemperature,
  postureLabel,
} from "../domain/format.js";
import { rhLimitedExplanation, simulatorStatusExplanation } from "../domain/explanations.js";
import { GLOSSARY } from "../domain/glossary.js";
import InfoTooltip from "./InfoTooltip.jsx";
import { Provenance, StatusBadge } from "./ResultCards.jsx";

// Grouped scenario conditions (visual redesign, spec §7): Exterior, Operación, Interior —
// small typographic hierarchy with provenance markers, not a large technical table. Reads
// only fields the API already returns (record.outdoor/scenario/occupancy/indoor); no new
// variable is introduced. `dimmed` mirrors the same "updating" state ResultCards shows.
//
// `fixedParams` (feedback round 2, point 17; round 6): vel/clo/posture always render as
// normal rows under "Operación" (values read from the record, never hardcoded). In guided
// mode, where they are not editable, a small "Fijos en el modo guiado" label precedes them;
// in simulation mode they ARE editable via ScenarioControls, so no "Fijos" wording.
export default function ConditionsPanel({ record, dimmed, fixedParams = false }) {
  const { outdoor, scenario, occupancy, indoor } = record;

  return (
    <section className={`conditions-panel${dimmed ? " is-updating" : ""}`} aria-busy={dimmed}>
      <div className="conditions-group">
        <h4>Exterior</h4>
        <dl>
          <div className="row">
            <dt>Temperatura exterior <Provenance record={record} field="tout" /></dt>
            <dd>{formatTemperature(outdoor.tout_c)}</dd>
          </div>
          <div className="row">
            <dt>Humedad exterior <Provenance record={record} field="rh_out" /></dt>
            <dd>{formatPercent(outdoor.rh_out)}</dd>
          </div>
        </dl>
      </div>

      <div className="conditions-group">
        <h4>Operación</h4>
        <dl>
          <div className="row">
            <dt>Línea</dt>
            <dd>Línea {scenario.line}</dd>
          </div>
          <div className="row">
            <dt>Hora</dt>
            <dd>{scenario.hour} h</dd>
          </div>
          <div className="row">
            <dt>Ocupación en hora pico <InfoTooltip text={GLOSSARY.phiPeak} /> <Provenance record={record} field="phi_peak" /></dt>
            <dd>{scenario.phi_peak}</dd>
          </div>
          <div className="row">
            <dt>Pasajeros <InfoTooltip text={GLOSSARY.n} /> <Provenance record={record} field="n" /></dt>
            <dd>{Math.round(occupancy.n)}</dd>
          </div>
          <div className="row">
            <dt>Tiempo de renovación de aire <InfoTooltip text={GLOSSARY.tauR} /> <Provenance record={record} field="tau_r" /></dt>
            <dd>{scenario.tau_r} s</dd>
          </div>
        </dl>
        {/* vel/clo/posture as ordinary rows in both modes (feedback round 6: the old inline
            "Fijos: ..." sentence showed gaps where its hidden provenance markers sat). In
            guided mode they sit under a small "Fijos en el modo guiado" label, since they
            cannot be changed there; in simulation mode they are plain rows. */}
        {fixedParams && <p className="conditions-subhead">Fijos en el modo guiado</p>}
        <dl className={fixedParams ? "conditions-fixed" : undefined}>
          <div className="row">
            <dt>Velocidad del aire <InfoTooltip text={GLOSSARY.vel} /> <Provenance record={record} field="vel" /></dt>
            <dd>{scenario.vel} m/s</dd>
          </div>
          <div className="row">
            <dt>Aislamiento de la ropa <InfoTooltip text={GLOSSARY.clo} /> <Provenance record={record} field="clo" /></dt>
            <dd>{scenario.clo} clo</dd>
          </div>
          <div className="row">
            <dt>Postura</dt>
            <dd>{postureLabel(scenario.posture)}</dd>
          </div>
        </dl>
      </div>

      <div className="conditions-group">
        <h4>Interior</h4>
        <dl>
          <div className="row">
            <dt>Temperatura interior <Provenance record={record} field="tin" /></dt>
            <dd>{formatTemperature(indoor.tin_c)}</dd>
          </div>
          <div className="row">
            <dt>Humedad interior <Provenance record={record} field="rh_in" /></dt>
            <dd>
              {formatPercent(indoor.rh_in)}
              {indoor.rh_limited && (
                <>
                  {" "}
                  <StatusBadge text="Humedad limitada" kind="warn" />
                  <InfoTooltip text={`${GLOSSARY.rhLimit} ${rhLimitedExplanation()}`} />
                </>
              )}
            </dd>
          </div>
          <div className="row">
            <dt>Diferencia de temperatura interior–exterior <InfoTooltip text={GLOSSARY.deltaT} /> <Provenance record={record} field="delta_t" /></dt>
            <dd>{indoor.delta_t != null ? `${indoor.delta_t.toFixed(1)} K` : "—"}</dd>
          </div>
        </dl>
        {indoor.simulator_status && (
          <p className="conditions-note">
            <StatusBadge text={indoor.simulator_status} kind="warn" />
            <InfoTooltip text={`${GLOSSARY.simulatorValidity} ${simulatorStatusExplanation(record)}`} />
          </p>
        )}
      </div>
    </section>
  );
}
