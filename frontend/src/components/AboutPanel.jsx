// Fact content stays fully backed by the project's own closed documents (see the module doc
// below) even though it no longer imports DISCLAIMER/ATTRIBUTION as separate paragraphs.
//
// "¿Qué estoy viendo?" (G-04, visual redesign §9; feedback round 3, direction 2026-09-26:
// a compact labeled pill fixed bottom-right, content reorganized into "the three panels" +
// "context" as the direction dictated): a brief, easy-to-close, non-blocking panel that opens above the
// bubble — not a modal, so it never captures clicks outside itself and the rest of the page
// stays interactive while it is open. Every fact here is taken from the project's own closed
// documents (README.md, PHASE_1_ARCHITECTURE.md §1/§2, PHASE_2_RESULTS.md §5/§8/§9,
// GUIDED_MODE.md §2/§3) — no number is invented. The known-model-limitation bullet is the
// same fact the header's removed "!!" marker used to carry (feedback round 2: the marker is
// gone, the information is not).
import { useCallback, useState } from "react";

import { REPOSITORY_URL } from "../domain/sources.js";

// True while the scrollable panel still has content below the visible area.
function hasMoreBelow(node) {
  return node.scrollHeight - node.scrollTop - node.clientHeight > 4;
}

export default function AboutPanel({ open, onToggle }) {
  const [moreBelow, setMoreBelow] = useState(false);
  // Callback ref: measures once the panel mounts (open), before any scroll event.
  const popoverRef = useCallback((node) => {
    if (node) setMoreBelow(hasMoreBelow(node));
  }, []);

  return (
    <>
      <button
        type="button"
        className="about-fab"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => onToggle(!open)}
      >
        ¿Qué estoy viendo?
      </button>

      {/* Small arrow pointing down from the open panel to its button (feedback round 5). A
          sibling, not a pseudo-element: the popover scrolls (overflow-y: auto), which would
          clip anything drawn outside its box. */}
      {open && <span className="about-popover-tail" aria-hidden="true" />}
      {open && (
        <div
          className="about-popover"
          ref={popoverRef}
          onScroll={(event) => setMoreBelow(hasMoreBelow(event.currentTarget))}
          role="dialog"
          aria-label="¿Qué estoy viendo?"
          onKeyDown={(event) => {
            if (event.key === "Escape") onToggle(false);
          }}
        >
          <div className="about-popover-header">
            <h3>¿Qué estoy viendo?</h3>
            <button type="button" className="about-close" aria-label="Cerrar" onClick={() => onToggle(false)}>
              ×
            </button>
          </div>

          <div className="about-content">
            <h4 className="about-section-title">Contexto</h4>
            <ul className="about-bullets">
              <li>
                Gemetro Digital estima el confort térmico de los pasajeros dentro de un vagón
                sin aire acondicionado de las líneas A y B del Metro de Medellín: un simulador
                físico calcula el ambiente interior del escenario y un modelo de machine
                learning, junto con el índice PMV, clasifica la sensación térmica.
              </li>
              <li>
                Proyecto académico y exploratorio. Los parámetros del escenario de Medellín se
                derivan de información documentada cuando existe (referirse al{" "}
                <a href={REPOSITORY_URL} target="_blank" rel="noreferrer noopener">repositorio</a>);
                cuando no, se estiman. Por eso es un pseudo digital twin:
                no tiene conexión en tiempo real con los trenes.
              </li>
              <li>
                El modelo de machine learning se entrenó y se evaluó con encuestas reales del
                metro de Nanjing; los escenarios de Medellín no son una validación empírica
                del modelo.
              </li>
              <li>
                "Dentro del dominio", "Fuera del dominio" y "Fuera de rango para PMV" son
                estados científicos, documentados y analizados dentro del alcance del proyecto
                (referirse al{" "}
                <a href={REPOSITORY_URL} target="_blank" rel="noreferrer noopener">repositorio</a>).
              </li>
            </ul>

            <h4 className="about-section-title">Los tres paneles</h4>
            <dl className="about-panels">
              <dt>Izquierda — modo y controles</dt>
              <dd>
                El modo guiado usa escenarios con datos derivados del Metro de Medellín
                (ocupación) y del clima de Medellín. El modo simulación permite ajustar
                libremente las variables del escenario que recibe el modelo.
              </dd>
              <dt>Centro — resultado</dt>
              <dd>
                Toma los parámetros del modo activo y muestra la clasificación de confort del
                modelo de machine learning y la del PMV, el esquema del vagón y las variables
                del escenario.
              </dd>
              <dt>Derecha — análisis</dt>
              <dd>
                Gráficas que relacionan el tiempo de renovación de aire con la temperatura
                interior; en modo simulación, también el perfil diario.
              </dd>
            </dl>
          </div>

          {/* Floating down arrow (feedback round 5): shown while there is more content below
              the fold, hidden once the panel is scrolled to the end. */}
          {moreBelow && (
            <span className="about-scroll-hint" aria-hidden="true">
              <svg viewBox="0 0 16 16">
                <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.5" />
              </svg>
            </span>
          )}
        </div>
      )}
    </>
  );
}
