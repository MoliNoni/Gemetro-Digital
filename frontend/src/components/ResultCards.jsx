import {
  classLabel,
  formatPmvValue,
  mlStatusKind,
  pmvStatusKind,
  ML_IN_DOMAIN_STATUS,
  PMV_VALID,
} from "../domain/format.js";
import {
  domainViolationList,
  mlDomainExplanation,
  pmvOutOfRangeExplanation,
  pmvViolationList,
} from "../domain/explanations.js";
import { GLOSSARY } from "../domain/glossary.js";
import InfoTooltip from "./InfoTooltip.jsx";

// Exported: also used by SensitivityChart and ConditionsPanel, which show the same badge
// style outside of ResultCards. `kind` is one of the four semantic tones only: "ok" (normal
// — in domain/valid; a neutral/positive tone, never green, so it never reads as "model
// verified correct"), "warn" (amber — out of domain, out of range: a scientific state, never
// an app error), "error" (red — reserved for a real technical/API failure, never used here),
// "muted" (gray — not comparable / secondary).
export function StatusBadge({ text, kind }) {
  return <span className={`status status-${kind}`}>{text}</span>;
}

// Provenance category for one field, as received from the API (never invented or
// reworded): a small hover/focus marker next to the value, per the redesign's "provenance
// in hover tooltips" requirement — the same accessible pattern as InfoTooltip (mounted at
// all times; only visibility toggles), but with its own trigger glyph/label so "explain the
// concept" (InfoTooltip's "?") and "where does this value come from" stay visually distinct.
export function Provenance({ record, field }) {
  const category = record.provenance?.[field];
  if (!category) return null;
  return <InfoTooltip text={category} glyph="●" label="Procedencia" className="provenance-tooltip" />;
}

// A status pill that is itself the hover/focus target for its explanation (visual QA fix:
// "tooltip on the status pill itself, keyboard-focusable") — not a separate icon next to
// it. Never renders a tooltip when there is nothing to explain (in-domain/valid/agree), so
// no permanent literal explanation sits under a normal result.
function StatusPill({ text, kind, tooltip, tooltipLabel }) {
  if (!tooltip) return <StatusBadge text={text} kind={kind} />;
  return (
    <InfoTooltip
      text={tooltip}
      label={tooltipLabel}
      className="status-pill-tooltip"
      glyph={<StatusBadge text={text} kind={kind} />}
    />
  );
}

// Short, calm label for the ML domain state — decoupled from the exact API status string
// (which keeps varying wording): always exactly "Dentro del dominio" / "Fuera del dominio".
// Never a permanent explanation next to it: the reasons live only in the pill's own tooltip.
function mlStateLabel(domainStatus) {
  return domainStatus === ML_IN_DOMAIN_STATUS ? "Dentro del dominio" : "Fuera del dominio";
}

// Central results block (visual QA fix): ML and PMV side by side in one panel — a single
// cohesive block with one border, not two orphan cards. `dimmed` reflects "updating" (the
// previous result stays mounted, only visually dimmed, a small loading indicator is shown by
// the caller). `domain` (/config.domain) and `pmvRanges` (/config.pmv_ranges) are optional:
// when given, the out-of-domain/out-of-range tooltip states each violated bound as a compact
// directional inequality (e.g. "RH 43 % < 52,05 %"); when omitted, the tooltip falls back to
// the full-sentence explanation (backward compatible with callers that do not have those
// bounds yet).
//
// Feedback round 2 (direction 2026-09-25, point 5): the ML/PMV comparison footer is removed
// entirely — each card already states its own class and validity state; domain/comparison.js
// and its unit tests are untouched, only unused here now.
export default function ResultCards({ record, dimmed, domain = null, pmvRanges = null }) {
  const { ml, pmv } = record;
  const mlKind = mlStatusKind(ml.domain_status);

  // The compact directional list is the whole tooltip when the bounds are available (§ visual
  // QA fix: no permanent literal sentence); the full sentence is only a fallback for a caller
  // that has not passed `domain`/`pmvRanges` at all.
  const mlViolations = domainViolationList(record, domain);
  const mlTooltipText = mlViolations.length > 0 ? mlViolations.join("  ·  ") : mlDomainExplanation(record, domain);

  const pmvViolations = pmvViolationList(record, pmvRanges);
  const pmvTooltipText = pmvViolations.length > 0 ? pmvViolations.join("  ·  ") : pmvOutOfRangeExplanation(record, pmvRanges);

  return (
    <section className={`result-panel${dimmed ? " is-updating" : ""}`} aria-busy={dimmed}>
      <div className="result-main">
        <div className="result-col result-ml">
          <h3>Confort según ML <InfoTooltip text={GLOSSARY.mlDomain} /> <Provenance record={record} field="ml_class" /></h3>
          <p className="value">{classLabel(ml.comfort_class)}</p>
          <p className="card-state">
            <StatusPill
              text={mlStateLabel(ml.domain_status)}
              kind={mlKind}
              tooltip={mlKind === "warn" ? mlTooltipText : null}
              tooltipLabel="Por qué está fuera del dominio"
            />
          </p>
        </div>

        <div className="result-col result-pmv">
          <h3>
            Confort según PMV <InfoTooltip text={GLOSSARY.pmv} />{" "}
            <InfoTooltip text={GLOSSARY.iso7730} label="Norma aplicada" glyph="§" />
          </h3>
          {pmv.status === PMV_VALID ? (
            <>
              <p className="value">{classLabel(pmv.comfort_class)}</p>
              <p className="pmv-value">PMV {formatPmvValue(pmv.value)}</p>
            </>
          ) : (
            <p className="card-state">
              <StatusPill
                text={pmv.status}
                kind={pmvStatusKind(pmv.status)}
                tooltip={pmvTooltipText}
                tooltipLabel="Por qué está fuera de rango"
              />
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
