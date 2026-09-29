// Skeletons that mirror the real layout blocks (same grid columns, panels and approximate
// heights) so the swap to real content causes no layout shift. They only render while no data
// exists yet; refetches keep the previous content dimmed instead (see GuidedMode/SimulationMode).
// The status text is visually hidden and rendered once per view, so screen readers announce
// a single "loading" message.
import Skeleton from "./Skeleton.jsx";

function SrStatus({ children }) {
  return <p className="sr-only" role="status">{children}</p>;
}

// Hour strip placeholder: one row of chips, same as the real `.hour-strip`.
export function HourStripSkeleton() {
  return (
    <div className="hour-strip skeleton-hour-strip" aria-hidden="true">
      {Array.from({ length: 5 }, (_, i) => (
        <Skeleton key={i} className="skeleton-hour-chip" />
      ))}
    </div>
  );
}

// Left column of guided mode: line, period and hour strip (only used for the initial config
// load; once config exists the real line/period buttons are shown).
function GuidedControlsSkeleton() {
  return (
    <div className="col-left guided-controls" aria-hidden="true">
      <Skeleton variant="line" width="30%" />
      <Skeleton className="skeleton-segmented" />
      <Skeleton variant="line" width="30%" />
      <Skeleton className="skeleton-segmented" />
      <Skeleton variant="line" width="30%" />
      <HourStripSkeleton />
    </div>
  );
}

// Wagon + ML/PMV result panel + conditions panel, as in the center column.
export function ResultsColumnSkeleton({ label }) {
  return (
    <div className="col-center skeleton-region" aria-busy="true">
      {label && <SrStatus>{label}</SrStatus>}
      <div className="wagon-block" aria-hidden="true">
        <Skeleton className="skeleton-wagon" />
        <Skeleton variant="line" width="70%" />
      </div>
      <div className="result-panel" aria-hidden="true">
        <div className="result-main">
          <div className="result-col">
            <Skeleton variant="line" width="45%" />
            <Skeleton className="skeleton-value" />
            <Skeleton variant="line" width="60%" />
          </div>
          <div className="result-col result-pmv">
            <Skeleton variant="line" width="45%" />
            <Skeleton className="skeleton-value" />
            <Skeleton variant="line" width="60%" />
          </div>
        </div>
      </div>
      <div className="conditions-panel" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <div key={i} className="conditions-group skeleton-conditions-group">
            <Skeleton variant="line" width="40%" />
            <Skeleton variant="line" />
            <Skeleton variant="line" />
          </div>
        ))}
      </div>
    </div>
  );
}

// A chart card (sensitivity / daily profile): title line plus a 220 px plot area, the same
// height the Recharts container reserves.
export function ChartSkeleton({ label }) {
  return (
    <div className="sensitivity-chart skeleton-region" aria-busy="true">
      {label && <SrStatus>{label}</SrStatus>}
      <Skeleton variant="line" width="50%" />
      <Skeleton className="skeleton-chart" />
    </div>
  );
}

// Right column with the sensitivity chart placeholder; simulation mode adds the daily one.
export function ChartsColumnSkeleton({ withDailyProfile = false }) {
  return (
    <div className="col-right">
      <ChartSkeleton />
      {withDailyProfile && <ChartSkeleton />}
    </div>
  );
}

// Initial /config load: the whole layout grid (mode switch slot + guided mode shape, since
// guided is the default view).
export function AppSkeleton() {
  return (
    <div className="layout-grid" aria-busy="true">
      <div className="col-left mode-switch-slot" aria-hidden="true">
        <Skeleton className="skeleton-segmented" />
      </div>
      <GuidedControlsSkeleton />
      <ResultsColumnSkeleton label="Conectando con el servicio…" />
      <ChartsColumnSkeleton />
    </div>
  );
}
