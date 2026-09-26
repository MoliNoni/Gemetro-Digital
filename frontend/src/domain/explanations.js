// One-line explanations built only from API fields (record.ml.out_of_domain,
// record.pmv.out_of_range, record.indoor.simulator_status/rh_limited). No number is
// hardcoded here: a bound is only ever added when the caller passes it in, and it always
// comes from the API (/config.domain or /config.pmv_ranges), never a literal in this file.

import { formatCommaNumber, formatPercent, formatTemperature, postureLabel, roundHalf } from "./format.js";

function roundTo(value, decimals) {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

// Formats one bound value (min or max of a domain/PMV range) with the unit matching its
// field, reusing the same rounding/formatting the rest of the app already uses for that
// unit. `rh`/`pa` come from the API already in percent/Pa (not a 0-1 fraction).
function formatBoundValue(field, value) {
  switch (field) {
    case "ta":
    case "tr":
      return formatTemperature(value);
    case "rh":
      return `${Math.round(value)} %`;
    case "vel":
      return `${roundTo(value, 2)} m/s`;
    case "clo":
      return `${roundTo(value, 2)} clo`;
    case "met":
      return `${roundTo(value, 1)} met`;
    case "pa":
      return `${Math.round(value)} Pa`;
    case "pmv":
      return `${roundTo(value, 1)}`;
    default:
      return `${value}`;
  }
}

// Optional bound note, e.g. " (rango de entrenamiento: 52 %–89 %)". Empty when no bounds
// config is passed (default, backward compatible) or when the field has no numeric bound
// (e.g. "posture").
function domainBoundsNote(reason, domain) {
  const bounds = domain?.[reason];
  if (!bounds) return "";
  return ` (rango de entrenamiento: ${formatBoundValue(reason, bounds.min)}–${formatBoundValue(reason, bounds.max)})`;
}

function pmvBoundsNote(reason, pmvRanges) {
  const bounds = pmvRanges?.[reason];
  if (!bounds) return "";
  return ` (rango válido: ${formatBoundValue(reason, bounds.min)}–${formatBoundValue(reason, bounds.max)})`;
}

// Each label already carries its article, so it reads correctly whether or not a value
// follows (e.g. "la temperatura interior" / "el aislamiento de la ropa").
const ML_FIELD_LABELS = {
  ta: "la temperatura interior",
  rh: "la humedad interior",
  vel: "la velocidad del aire",
  clo: "el aislamiento de la ropa",
  posture: "la postura",
};

const PMV_FIELD_LABELS = {
  ta: "la temperatura interior",
  tr: "la temperatura radiante",
  pa: "la presión de vapor",
  vel: "la velocidad del aire",
  met: "la tasa metabólica",
  clo: "el aislamiento de la ropa",
  pmv: "el valor de PMV",
};

function mlFieldValue(reason, record) {
  switch (reason) {
    case "ta":
      return formatTemperature(record.indoor.tin_c);
    case "rh":
      return formatPercent(record.indoor.rh_in);
    case "vel":
      return `${record.scenario.vel} m/s`;
    case "clo":
      return `${record.scenario.clo} clo`;
    case "posture":
      return postureLabel(record.scenario.posture);
    default:
      return null;
  }
}

// e.g. "La humedad interior (43 %) está fuera del rango de los datos de Nanjing con los que
// se entrenó el modelo." With `domain` (/config.domain), also states that field's training
// bounds, e.g. "... el modelo (rango de entrenamiento: 52 %–89 %)."; omitted when `domain`
// is not passed (default), which reproduces the previous no-bound text unchanged.
export function mlDomainExplanation(record, domain = null) {
  const reasons = record.ml.out_of_domain;
  if (!reasons || reasons.length === 0) return "";
  return reasons
    .map((reason) => {
      const label = ML_FIELD_LABELS[reason] ?? reason;
      const value = mlFieldValue(reason, record);
      const subject = value ? `${label} (${value})` : label;
      const capitalized = subject.charAt(0).toUpperCase() + subject.slice(1);
      const bound = domainBoundsNote(reason, domain);
      return `${capitalized} está fuera del rango de los datos de Nanjing con los que se entrenó el modelo${bound}.`;
    })
    .join(" ");
}

// e.g. "La temperatura interior de este escenario está fuera de los rangos de validez de
// ISO 7730." With `pmvRanges` (/config.pmv_ranges), also states that field's valid range;
// omitted when `pmvRanges` is not passed (default), reproducing the previous text unchanged.
export function pmvOutOfRangeExplanation(record, pmvRanges = null) {
  const reasons = record.pmv.out_of_range;
  if (!reasons || reasons.length === 0) return "";
  return reasons
    .map((reason) => {
      const label = PMV_FIELD_LABELS[reason] ?? reason;
      const subject = label.charAt(0).toUpperCase() + label.slice(1);
      const bound = pmvBoundsNote(reason, pmvRanges);
      return `${subject} de este escenario está fuera de los rangos de validez de ISO 7730${bound}.`;
    })
    .join(" ");
}

// e.g. "La temperatura interior simulada (55.0 °C) supera el límite de validez de la fórmula
// usada por el simulador." No bound number is stated (it is not returned by the API).
export function simulatorStatusExplanation(record) {
  if (!record.indoor.simulator_status) return "";
  return `La temperatura interior simulada (${formatTemperature(record.indoor.tin_c)}) ` +
    "supera el límite de validez de la fórmula usada por el simulador.";
}

export function rhLimitedExplanation() {
  return "La humedad relativa simulada alcanzó el límite físico de 100 % y se recortó a ese valor.";
}

// --- Compact directional-inequality tooltip content (visual redesign) --------------------
//
// Short, per-variable lines for the ML/PMV hover tooltips (e.g. "RH 43 % < 52,05 %"), which
// are now the tooltip's whole content (visual QA fix: no permanent literal explanation
// anywhere in the results). The full-sentence explanations above remain as a fallback for a
// caller that has not passed the /config bounds at all.
// Every value here is read directly from the record/config the API returned; nothing is
// invented, and a field is only ever compared against a bound the API actually provided.

const SHORT_FIELD_LABELS = { ta: "Ta", rh: "RH", tr: "Tr", vel: "Vel", clo: "Clo", met: "Met", pa: "Pa", pmv: "PMV" };

// The current value, formatted with the same precision the rest of the UI already uses for
// that quantity (temperature: half-degree steps/1 decimal via roundHalf; RH: whole percent
// via Math.round — no decimal comma needed on a whole number), just with the decimal comma
// applied where there is one.
function formatCurrentValue(field, value) {
  switch (field) {
    case "ta":
    case "tr":
      return `${formatCommaNumber(roundHalf(value), 1)} °C`;
    case "rh":
      return `${Math.round(value)} %`;
    case "vel":
      return `${formatCommaNumber(value, 2)} m/s`;
    case "clo":
      return `${formatCommaNumber(value, 2)} clo`;
    case "met":
      return `${formatCommaNumber(value, 2)} met`;
    default:
      return `${value}`;
  }
}

// The bound value (min/max of /config.domain or /config.pmv_ranges), kept at the precision
// the API itself returned it (e.g. domain.rh.min === 52.05) — never re-rounded to match the
// coarser current-value display, so the compact line always cites the exact configured
// limit ("RH 43 % < 52,05 %").
function formatBoundValueComma(field, value) {
  switch (field) {
    case "ta":
    case "tr":
      return `${formatCommaNumber(value, 2)} °C`;
    case "rh":
      return `${formatCommaNumber(value, 2)} %`;
    case "vel":
      return `${formatCommaNumber(value, 2)} m/s`;
    case "clo":
      return `${formatCommaNumber(value, 2)} clo`;
    case "met":
      return `${formatCommaNumber(value, 2)} met`;
    case "pa":
      return `${formatCommaNumber(value, 0)} Pa`;
    default:
      return `${value}`;
  }
}

// The current numeric value for one ML domain field, in the same unit as `/config.domain`
// (rh_in is a 0-1 fraction in the record; domain.rh is in percent). Returns null when the
// field has no numeric current value in the record (e.g. "posture").
function mlRawValue(field, record) {
  switch (field) {
    case "ta":
      return record.indoor.tin_c;
    case "rh":
      return record.indoor.rh_in * 100;
    case "vel":
      return record.scenario.vel;
    case "clo":
      return record.scenario.clo;
    default:
      return null;
  }
}

// One compact directional line per violated ML domain field, e.g. "RH 45,30 % < 52,05 %".
// Requires `domain` (/config.domain); returns [] when it is not available (never a guessed
// bound) or when there is nothing out of domain.
export function domainViolationList(record, domain) {
  const reasons = record.ml.out_of_domain;
  if (!reasons || reasons.length === 0 || !domain) return [];
  return reasons
    .map((field) => {
      if (field === "posture") {
        const allowed = domain.postures;
        return allowed
          ? `Postura (${postureLabel(record.scenario.posture)}) fuera de las reconocidas por el modelo (${allowed.map(postureLabel).join(", ")})`
          : null;
      }
      const bounds = domain[field];
      const value = mlRawValue(field, record);
      if (!bounds || value == null) return null;
      const label = SHORT_FIELD_LABELS[field] ?? field;
      if (value < bounds.min) {
        return `${label} ${formatCurrentValue(field, value)} < ${formatBoundValueComma(field, bounds.min)}`;
      }
      if (value > bounds.max) {
        return `${label} ${formatCurrentValue(field, value)} > ${formatBoundValueComma(field, bounds.max)}`;
      }
      return null;
    })
    .filter(Boolean);
}

// The current numeric value for one PMV validity field. `tr` and `pa` are not returned by
// the API as standalone fields (tr = ta is a documented methodological assumption in
// src/gemetro/pmv.py; pa is derived internally), so those two report the bound without a
// current value rather than inventing one.
function pmvRawValue(field, record) {
  switch (field) {
    case "ta":
      return record.indoor.tin_c;
    case "tr":
      return record.indoor.tin_c; // tr = ta (pmv.py methodological assumption)
    case "vel":
      return record.scenario.vel;
    case "clo":
      return record.scenario.clo;
    case "met":
      return record.met;
    default:
      return null;
  }
}

// One compact directional line per violated PMV validity field. Requires `pmvRanges`
// (/config.pmv_ranges); returns [] when unavailable or nothing is out of range.
export function pmvViolationList(record, pmvRanges) {
  const reasons = record.pmv.out_of_range;
  if (!reasons || reasons.length === 0 || !pmvRanges) return [];
  return reasons
    .map((field) => {
      const bounds = pmvRanges[field];
      if (!bounds) return null;
      const label = SHORT_FIELD_LABELS[field] ?? field;
      const value = pmvRawValue(field, record);
      if (value == null) {
        return `${label} fuera del rango válido (${formatBoundValueComma(field, bounds.min)}–${formatBoundValueComma(field, bounds.max)})`;
      }
      if (value < bounds.min) {
        return `${label} ${formatCurrentValue(field, value)} < ${formatBoundValueComma(field, bounds.min)}`;
      }
      if (value > bounds.max) {
        return `${label} ${formatCurrentValue(field, value)} > ${formatBoundValueComma(field, bounds.max)}`;
      }
      return null;
    })
    .filter(Boolean);
}
