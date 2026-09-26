import { formatTemperature } from "../domain/format.js";
import { Provenance } from "./ResultCards.jsx";
import InfoTooltip from "./InfoTooltip.jsx";

// Small secondary indicators around the wagon (visual redesign §4): temperature, radiant
// temperature, air speed and occupancy, all read from the same record ResultCards/
// ConditionsPanel already use — no new value is computed here. `tr` is not a field the API
// returns on its own: src/gemetro/pmv.py documents "tr = ta" as a methodological assumption,
// so it is shown here as that same Tin value with its own tooltip stating the assumption,
// rather than inventing a distinct number.
export default function WagonIndicators({ record }) {
  const { indoor, scenario, occupancy } = record;
  return (
    <dl className="wagon-indicators">
      <div className="wagon-indicator">
        <dt>Temperatura interior</dt>
        <dd>{formatTemperature(indoor.tin_c)} <Provenance record={record} field="tin" /></dd>
      </div>
      <div className="wagon-indicator">
        <dt>Temperatura radiante</dt>
        <dd>
          {formatTemperature(indoor.tin_c)}{" "}
          <InfoTooltip text="Supuesto metodológico del PMV: tr = ta (temperatura radiante igual a la temperatura del aire). No es una medición aparte." />
        </dd>
      </div>
      <div className="wagon-indicator">
        <dt>Velocidad del aire</dt>
        <dd>{scenario.vel} m/s</dd>
      </div>
      <div className="wagon-indicator">
        <dt>Pasajeros</dt>
        <dd>{Math.round(occupancy.n)}</dd>
      </div>
    </dl>
  );
}
