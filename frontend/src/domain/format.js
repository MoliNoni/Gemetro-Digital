// Pure presentation helpers, ported from the previous static frontend's render.js.
// The frontend computes no model value: rounding here is presentation only
// (Tin/ΔT to 0.5 °C, RH to 1 %, PMV to 0.1), and every label maps a value the API
// already returned, never a threshold or bound.

export const CLASS_LABELS = { cool: "fresco", neutral: "neutral", warm: "cálido" };
export const POSTURE_LABELS = { seated: "Sentado", standing: "De pie" };
export const PMV_VALID = "valid";
export const ML_IN_DOMAIN_STATUS = "Dentro del dominio de entrenamiento";

export function roundHalf(value) {
  return Math.round(value * 2) / 2;
}

export function formatTemperature(value) {
  return `${roundHalf(value).toFixed(1)} °C`;
}

export function formatPercent(fraction) {
  return `${Math.round(fraction * 100)} %`;
}

export function formatPmvValue(value) {
  return value.toFixed(1);
}

// Spanish decimal-comma formatting, used only by the compact directional bound labels in
// the ML/PMV hover tooltips (e.g. "RH 45,30 % < 52,05 %") — every other existing label in
// this file keeps its original dot-decimal formatting so existing tests/output are
// unaffected.
export function formatCommaNumber(value, decimals = 2) {
  return value.toFixed(decimals).replace(".", ",");
}

export function classLabel(comfortClass) {
  return CLASS_LABELS[comfortClass] ?? comfortClass;
}

export function postureLabel(posture) {
  return POSTURE_LABELS[posture] ?? posture;
}

// "ok" (in-domain / valid) vs "warn" (extrapolation / out of range / simulator invalid).
// Extrapolation is an informational amber state, never an error state.
export function mlStatusKind(domainStatus) {
  return domainStatus === ML_IN_DOMAIN_STATUS ? "ok" : "warn";
}

export function pmvStatusKind(status) {
  return status === PMV_VALID ? "ok" : "warn";
}

export const DISCLAIMER =
  "Pseudo Digital Twin: simulación académica de escenarios de un vagón de las líneas A y B. " +
  "No es un sistema oficial del Metro de Medellín, no tiene conexión en tiempo real con los " +
  "trenes y sus resultados no están validados con mediciones en Medellín.";

export const UNCERTAINTY_NOTE = "La incertidumbre dominante es la ventilación efectiva.";

export const ATTRIBUTION =
  "Fuentes: IDEAM, estación Olaya Herrera (datos.gov.co, CC BY-SA 4.0); Metro de Medellín, " +
  "afluencia 2025 y GTFS 2025 (licencia no declarada); modelo de confort entrenado con " +
  "encuestas en vagones del metro de Nanjing; PMV según ISO 7730.";
