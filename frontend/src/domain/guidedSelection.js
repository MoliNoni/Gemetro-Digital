// Pure helpers for guided mode (GUIDED_MODE.md §3, backed by GET /guided). The API already
// selects τr per hour (gemetro.guided.select_tau_r); the only decision left to the frontend
// is which hour of the period to show first, left open by GUIDED_MODE.md §5:
// "Decisiones taken during implementation" in odd/tasks/frontend-guided-mode.md: highest
// domain coverage, ties to the earliest hour.

// `entries` is `guided.entries` from GET /guided, one per hour of the period, in ascending
// hour order (gemetro.guided.period_hours). Returns the entry to show by default, or null
// for an empty list.
export function defaultEntry(entries) {
  if (!entries || entries.length === 0) return null;
  return entries.reduce((best, entry) => {
    if (best === null) return entry;
    // Ascending hour order + strict "greater than" means the first (earliest) hour at the
    // maximum coverage is kept on a tie.
    return entry.coverage.in_domain > best.coverage.in_domain ? entry : best;
  }, null);
}

export function entryByHour(entries, hour) {
  return entries?.find((entry) => entry.hour === hour) ?? null;
}
