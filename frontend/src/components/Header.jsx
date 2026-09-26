// Compact header (visual redesign §2): title, one-line subtitle and a discreet status
// badge — "Modelo experimental", never "modelo preciso"/"predicción validada" or an
// equivalent claim. The longer disclaimer, the ML-vs-simulation distinction and the known
// model limitation live in the "¿Qué estoy viendo?" panel (AboutPanel), reachable from its
// own floating bubble (feedback round 2, direction 2026-09-25) — never more than one click
// away, nothing here is hidden, only moved out of the header's fixed budget.
import { REPOSITORY_URL } from "../domain/sources.js";

// GitHub mark (feedback round 5): links to the author's GitHub profile, top-right.
const GITHUB_MARK =
  "M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z";

export default function Header() {
  return (
    <header className="app-header">
      <div className="app-header-titles">
        {/* Wordmark (feedback round 2): reuses the app's own sans + mono stacks instead of a
            new font — "Gemetro" set display-tight (negative tracking, like Linear's
            headings), "Digital" set as a small wide-tracked mono label under/after it, the
            way an instrument panel (Ableton, JPL) labels a system name next to its title. */}
        <h1>
          <span className="wordmark-main">Gemetro</span> <span className="wordmark-sub">Digital</span>
        </h1>
        <p className="app-subtitle">pseudo digital twin experimental de confort térmico</p>
      </div>
      <div className="app-header-status">
        <span className="status-badge-experimental">Modelo experimental</span>
        <a
          className="header-github"
          href={REPOSITORY_URL}
          target="_blank"
          rel="noreferrer noopener"
          aria-label="Perfil de GitHub"
          title="GitHub"
        >
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d={GITHUB_MARK} fill="currentColor" />
          </svg>
        </a>
      </div>
    </header>
  );
}
