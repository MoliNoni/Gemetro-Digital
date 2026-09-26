import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";

import { classLabel, formatTemperature, mlStatusKind, pmvStatusKind } from "../domain/format.js";
import { StatusBadge } from "./ResultCards.jsx";
import InfoTooltip from "./InfoTooltip.jsx";

const PREFERS_REDUCED_MOTION =
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// A "nice" rounded axis domain (visual QA fix round 3): the raw dataMin/dataMax the API
// returns can carry long floating-point tails (e.g. 20.999999999999996), which showed up
// verbatim as an axis tick when the domain was an unrounded "dataMin - 2"/"dataMax + 2"
// expression. Rounding the domain itself to a multiple of 5 °C, plus the integer
// `tickFormatter` below, keeps every tick a clean whole number regardless of what the raw
// data looks like. Recharts calls the first function with the computed dataMin and the
// second with the computed dataMax.
const niceFloor5 = (dataMin) => Math.floor(dataMin / 5) * 5;
const niceCeil5 = (dataMax) => Math.ceil(dataMax / 5) * 5;

// Explicit ticks every 5 °C (10 °C for wide ranges) across the rounded data range, so the
// axis never shows irregular steps such as 25/33/41 °C.
function fiveDegreeTicks(points) {
  const values = points.map((point) => point.tin_c);
  const low = niceFloor5(Math.min(...values));
  const high = niceCeil5(Math.max(...values));
  const step = high - low > 20 ? 10 : 5;
  const ticks = [];
  for (let tick = low; tick <= high; tick += step) ticks.push(tick);
  return ticks;
}

function integerDegreesTick(value) {
  return `${Math.round(value)} °C`;
}

// Feedback round 2 (direction 2026-09-25, point 6): the 240 s point is excluded from
// display — it is always out of the PMV range, so showing it added no useful information.
// Display-only: the API sweep and its data are unchanged; this filters only what the chart
// and table render.
const EXCLUDED_TAU_R_S = [240];

// τr sensitivity (F-04/G-03): the eight-point sweep `record.sensitivity` already returned by
// /scenario and /guided, each point with its own ML/PMV status (minus the excluded point
// above). The chart plots Tin per τr; the status of every point is also listed as plain text
// below it (P-27: visible without interaction, a hover-only tooltip would not satisfy that),
// and the currently selected τr (record.scenario.tau_r, only meaningful in normal mode) is
// marked on the chart and in the list. `pragueReferenceS` is only ever drawn as a labeled
// external reference (never a τr value or a Medellín datum), per the React redesign's closed
// constraint.
export default function SensitivityChart({ record, pragueReferenceS }) {
  const points = record.sensitivity.filter((point) => !EXCLUDED_TAU_R_S.includes(point.tau_r));
  const selectedTauR = record.scenario.mode === "normal" ? record.scenario.tau_r : null;

  return (
    <div className="sensitivity-chart">
      <h3>
        Sensibilidad al tiempo de renovación de aire{" "}
        <InfoTooltip
          label="Referencia de Praga"
          text={`La línea discontinua de Praga (~${pragueReferenceS} s) es una referencia externa de la literatura, no un dato de Medellín.`}
        />
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={points} margin={{ top: 12, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
          <XAxis
            dataKey="tau_r"
            type="number"
            domain={["dataMin", "dataMax"]}
            unit=" s"
            axisLine={{ stroke: "var(--line)" }}
            tickLine={{ stroke: "var(--line)" }}
            tick={{ fill: "var(--muted)", fontSize: 12 }}
          />
          <YAxis
            width={60}
            domain={[niceFloor5, niceCeil5]}
            ticks={fiveDegreeTicks(points)}
            tickFormatter={integerDegreesTick}
            axisLine={{ stroke: "var(--line)" }}
            tickLine={{ stroke: "var(--line)" }}
            tick={{ fill: "var(--muted)", fontSize: 12 }}
          />
          {/* No on-chart text label here (visual QA fix round 3: it collided with the y-axis
              top tick even when short) — just the dashed reference line itself; the
              "external reference, not a Medellín datum" explanation lives only in the
              caption below the chart. */}
          <ReferenceLine x={pragueReferenceS} stroke="var(--muted)" strokeDasharray="4 4" />
          {selectedTauR != null && (
            <ReferenceLine x={selectedTauR} stroke="var(--fg)" strokeDasharray="2 2" />
          )}
          <Line
            type="monotone"
            dataKey="tin_c"
            stroke="var(--fg)"
            strokeWidth={2}
            dot
            isAnimationActive={!PREFERS_REDUCED_MOTION}
          />
        </LineChart>
      </ResponsiveContainer>
      <table className="tau-table">
        <caption className="sr-only">
          Tabla de sensibilidad al tiempo de renovación de aire: temperatura interior y estado ML/PMV por punto
        </caption>
        <thead>
          <tr>
            <th scope="col">Renovación</th>
            <th scope="col">T. interior</th>
            <th scope="col">ML</th>
            <th scope="col">PMV</th>
          </tr>
        </thead>
        <tbody>
          {points.map((point) => {
            const mlWarn = mlStatusKind(point.ml.domain_status) === "warn";
            const pmvWarn = pmvStatusKind(point.pmv.status) === "warn";
            return (
              <tr
                key={point.tau_r}
                className={
                  `${point.tau_r === selectedTauR ? "is-selected " : ""}` +
                  `${mlWarn || pmvWarn ? "is-out-of-domain" : ""}`
                }
              >
                <td className="sensitivity-tau">{point.tau_r} s</td>
                <td className="sensitivity-tin">{formatTemperature(point.tin_c)}</td>
                <td>
                  <StatusBadge text={classLabel(point.ml.comfort_class)} kind={mlStatusKind(point.ml.domain_status)} />
                </td>
                <td>
                  <StatusBadge
                    text={point.pmv.status === "valid" ? classLabel(point.pmv.comfort_class) : point.pmv.status}
                    kind={pmvStatusKind(point.pmv.status)}
                  />
                  {point.simulator_status && (
                    <span className="simulator-note">
                      <StatusBadge text={point.simulator_status} kind="warn" />
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
