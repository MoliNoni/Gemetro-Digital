import { useEffect, useRef, useState } from "react";

import { runDayProfile } from "../api/client.js";

// Fetches the day profile (config.sliders.hour.min..max) for the current non-hour
// parameters and caches it by that parameter set: changing only the hour/preset must not
// refetch (it reuses the cache). `httpStatus` surfaces a 503 (model unavailable) the same
// way useScenario does. `nonHourParams` is null when the caller does not want this (costly:
// one request per hour) profile fetched yet (e.g. simulation mode not shown) — a no-op.
export function useDayProfile(nonHourParams, config) {
  const [state, setState] = useState({ status: "loading", points: null, error: null, httpStatus: null });
  const cacheRef = useRef(new Map());
  const requestIdRef = useRef(0);
  const [retryToken, setRetryToken] = useState(0);
  const key = config && nonHourParams ? JSON.stringify(nonHourParams) : null;

  useEffect(() => {
    if (!config || key === null) return undefined;

    const cached = cacheRef.current.get(key);
    if (cached) {
      setState({ status: "result", points: cached, error: null, httpStatus: null });
      return undefined;
    }

    const id = ++requestIdRef.current;
    const controller = new AbortController();
    setState((prev) => ({ status: "loading", points: prev.points, error: null, httpStatus: null }));

    runDayProfile(nonHourParams, config, { signal: controller.signal })
      .then((points) => {
        if (id !== requestIdRef.current) return;
        cacheRef.current.set(key, points);
        setState({ status: "result", points, error: null, httpStatus: null });
      })
      .catch((error) => {
        if (controller.signal.aborted || id !== requestIdRef.current) return;
        setState({ status: "error", points: null, error: error.message, httpStatus: error.status ?? null });
      });

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, config, retryToken]);

  return { ...state, retry: () => setRetryToken((n) => n + 1) };
}
