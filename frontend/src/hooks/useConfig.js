import { useEffect, useState } from "react";

import { fetchConfig } from "../api/client.js";

// Loads /config once. Sliders, ranges, defaults, domain, pmv_ranges and guided periods all
// come from here so they are never duplicated in the frontend. `httpStatus` lets callers
// show a specific "model unavailable" message for a 503 without re-parsing `error`.
export function useConfig() {
  const [state, setState] = useState({ status: "loading", config: null, error: null, httpStatus: null });
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setState((prev) => ({ status: "loading", config: prev.config, error: null, httpStatus: null }));
    fetchConfig({ signal: controller.signal })
      .then((config) => setState({ status: "result", config, error: null, httpStatus: null }))
      .catch((error) => {
        if (controller.signal.aborted) return;
        setState({ status: "error", config: null, error: error.message, httpStatus: error.status ?? null });
      });
    return () => controller.abort();
  }, [reloadToken]);

  return { ...state, refetch: () => setReloadToken((n) => n + 1) };
}
