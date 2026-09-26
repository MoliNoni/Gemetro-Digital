import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";

import { ML_IN_DOMAIN_STATUS, PMV_VALID } from "../domain/format.js";
import InfoTooltip from "./InfoTooltip.jsx";

const PREFERS_REDUCED_MOTION =
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const OK_COLOR = "var(--tone-ok-fg)";
const WARN_COLOR = "var(--tone-warn-fg)";

// Same "nice" rounded domain / integer tick fix as SensitivityChart.jsx (visual QA fix
// round 3): the raw Tin values can carry long floating-point tails, which showed up
// verbatim on the y-axis without this.
const niceFloor5 = (dataMin) => Math.floor(dataMin / 5) * 5;
const niceCeil5 = (dataMax) => Math.ceil(dataMax / 5) * 5;

function integerDegreesTick(value) {
  return `${Math.round(value)} °C`;
}

// Colors each hour's dot by its ML domain status, so the per-hour state is visible on the
// chart itself, without a hover.
function StatusDot({ cx, cy, payload }) {
  const inDomain = payload.record.ml.domain_status === ML_IN_DOMAIN_STATUS;
  return <circle cx={cx} cy={cy} r={4} fill={inDomain ? OK_COLOR : WARN_COLOR} />;
}

// Daily profile (F-04/G-03, simulation mode only): Tin across the full hour range
// (config.sliders.hour.min..max) for the current non-hour parameters (useDayProfile),
// highlighting the currently selected hour. Every dot is colored by ML domain status
// (visible without interaction); a low-opacity amber band additionally shades every
// ML-out-of-domain hour and a hatched gray band marks every PMV-out-of-range hour (visual
// QA fix round 3: states visible along the whole day, not only as text below) — both bands
// come only from the API points, never a hardcoded hour range. The two textual summaries
// below still list exactly which hours are affected (states, not an explanation, so they
// stay visible outside the tooltip); the chart mechanics themselves (axes, dot color, band
// meaning) are explained in the title's InfoTooltip (feedback round 2, point 18).
export default function DailyProfileChart({ points, selectedHour }) {
  const data = points.map(({ hour, record }) => ({ hour, tin_c: record.indoor.tin_c, record }));
  const mlOutHours = points.filter((p) => p.record.ml.domain_status !== ML_IN_DOMAIN_STATUS).map((p) => p.hour);
  const pmvOutHours = points.filter((p) => p.record.pmv.status !== PMV_VALID).map((p) => p.hour);
  // Half the hour step, derived from the API's own points (never a hardcoded assumption),
  // so each shaded band is centered on its hour and touches its neighbors with no gap.
  const halfStep = points.length > 1 ? (points[1].hour - points[0].hour) / 2 : 0.5;

  return (
    <div className="daily-profile-chart">
      <h3>
        Perfil diario{" "}
        <InfoTooltip
          text={
            "El eje horizontal es la hora; el eje vertical, la temperatura interior simulada " +
            "para los parámetros actuales (los que no son la hora). El color de cada punto " +
            "indica el estado de dominio del ML. La banda ámbar marca las horas con el ML " +
            "fuera del dominio; la banda rayada, las horas con el PMV fuera de rango. La " +
            "línea discontinua marca la hora seleccionada."
          }
        />
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 28, left: 0, bottom: 8 }}>
          <defs>
            <pattern id="pmv-out-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke="var(--tone-muted-fg)" strokeWidth="2" />
            </pattern>
          </defs>
          <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
          <XAxis
            dataKey="hour"
            type="number"
            domain={["dataMin", "dataMax"]}
            unit=" h"
            axisLine={{ stroke: "var(--line)" }}
            tickLine={{ stroke: "var(--line)" }}
            tick={{ fill: "var(--muted)", fontSize: 12 }}
          />
          <YAxis
            width={60}
            domain={[niceFloor5, niceCeil5]}
            tickFormatter={integerDegreesTick}
            axisLine={{ stroke: "var(--line)" }}
            tickLine={{ stroke: "var(--line)" }}
            tick={{ fill: "var(--muted)", fontSize: 12 }}
          />
          {mlOutHours.map((hour) => (
            <ReferenceArea
              key={`ml-out-${hour}`}
              x1={hour - halfStep}
              x2={hour + halfStep}
              fill={WARN_COLOR}
              fillOpacity={0.14}
              stroke="none"
            />
          ))}
          {pmvOutHours.map((hour) => (
            <ReferenceArea
              key={`pmv-out-${hour}`}
              x1={hour - halfStep}
              x2={hour + halfStep}
              fill="url(#pmv-out-hatch)"
              fillOpacity={0.7}
              stroke="none"
            />
          ))}
          <ReferenceLine x={selectedHour} stroke="var(--fg)" strokeDasharray="2 2" />
          <Line
            type="monotone"
            dataKey="tin_c"
            stroke="var(--fg)"
            strokeWidth={2}
            dot={<StatusDot />}
            isAnimationActive={!PREFERS_REDUCED_MOTION}
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="explanation">
        {mlOutHours.length === 0
          ? "El ML está dentro del dominio de entrenamiento en todas las horas de este escenario."
          : `El ML está en extrapolación en: ${mlOutHours.map((h) => `${h} h`).join(", ")}.`}
      </p>
      <p className="explanation">
        {pmvOutHours.length === 0
          ? "El PMV está dentro de rango en todas las horas de este escenario."
          : `El PMV está fuera de rango en: ${pmvOutHours.map((h) => `${h} h`).join(", ")}.`}
      </p>
    </div>
  );
}
