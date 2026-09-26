import { REPOSITORY_URL, SOURCE_GROUPS } from "../domain/sources.js";

// Page footer (feedback round 4, direction 2026-09-26): every data/reference source the
// project uses, grouped by what it feeds, plus the repository link where each source is
// documented in detail (DATA_SOURCES.md). Plain secondary text, no decoration.
export default function Footer() {
  return (
    <footer className="app-footer">
      {/* Collapsed by default (feedback round 5): one compact "Fuentes" row with a chevron;
          the full list only takes space once opened. Native <details>, keyboard-accessible. */}
      <details className="app-footer-details">
        <summary>
          <h2 className="app-footer-title">Fuentes</h2>
          <svg className="app-footer-chevron" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.5" />
          </svg>
        </summary>
        <div className="app-footer-groups">
          {SOURCE_GROUPS.map((group) => (
            <section key={group.title} className="app-footer-group">
              <h3>{group.title}</h3>
              <ul>
                {group.items.map((item) => (
                  <li key={item.text}>
                    {item.url ? (
                      <a href={item.url} target="_blank" rel="noreferrer noopener">
                        {item.text}
                      </a>
                    ) : (
                      item.text
                    )}
                  </li>
                ))}
              </ul>
            </section>
        ))}
      </div>
      <p className="app-footer-repo">
        Detalle de cada fuente, licencias y metodología en el repositorio:{" "}
        <a href={REPOSITORY_URL} target="_blank" rel="noreferrer noopener">
          github.com/MoliNoni
        </a>
      </p>
      </details>
    </footer>
  );
}
