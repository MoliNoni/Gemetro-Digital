import { useEffect, useState } from "react";

import { defaultEntry } from "../domain/guidedSelection.js";
import { useGuided } from "./useGuided.js";

export const GUIDED_PERIOD_ORDER = ["morning", "midday", "afternoon", "night"];

function periodForHour(periods, hour) {
  return GUIDED_PERIOD_ORDER.find((name) => periods[name]?.includes(hour)) ?? GUIDED_PERIOD_ORDER[0];
}

// Guided-mode selection state (line, period, selected hour) plus its GET /guided result,
// owned by App instead of GuidedMode (feedback round 5, direction 2026-09-26): GuidedMode
// unmounts while simulation mode is shown, and keeping this state in the component made
// every return to guided mode start empty and refetch, so the left and center columns
// blinked out for a moment. Held here, the last result and the user's picks survive the
// mode switch and nothing is refetched unless line/period actually change.
//
// The default period is the one containing the closed default scenario's hour (line A,
// 16 h -> "afternoon"). `config` may still be null on the first render (it loads
// asynchronously), so line/period fall back to the config defaults until the user picks.
export function useGuidedSelection(config) {
  const [pickedLine, setLine] = useState(null);
  const [pickedPeriod, setPeriod] = useState(null);
  const [selectedHour, setSelectedHour] = useState(null);

  const line = pickedLine ?? config?.defaults.line ?? null;
  const period =
    pickedPeriod ?? (config ? periodForHour(config.guided.periods, config.defaults.hour) : null);

  const guided = useGuided(line, period);

  // Recomputes the default hour (highest coverage, ties to the earliest hour) every time a
  // new line/period result arrives; a manual pick in the hour strip only lasts until then.
  useEffect(() => {
    if (!guided.data) return;
    setSelectedHour(defaultEntry(guided.data.entries)?.hour ?? null);
  }, [guided.data]);

  return { line, setLine, period, setPeriod, selectedHour, setSelectedHour, ...guided };
}
