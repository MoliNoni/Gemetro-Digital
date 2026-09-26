import { useEffect, useRef, useState } from "react";

import { fetchGuided } from "../api/client.js";

// Loads GET /guided for one line/period, discarding stale/out-of-order responses and
// keeping the previous result visible (status "updating") while a new one loads, the same
// pattern as useScenario. `httpStatus` surfaces a 503 (model unavailable) explicitly.
export function useGuided(line, period) {
  const [state, setState] = useState({ status: "loading", data: null, error: null, httpStatus: null });
  const [retryToken, setRetryToken] = useState(0);
  const requestIdRef = useRef(0);

  useEffect(() => {
    if (!line || !period) return undefined;
    const id = ++requestIdRef.current;
    const controller = new AbortController();
    setState((prev) => ({
      status: prev.data ? "updating" : "loading",
      data: prev.data,
      error: null,
      httpStatus: null,
    }));

    fetchGuided(line, period, { signal: controller.signal })
      .then((data) => {
        if (id !== requestIdRef.current) return;
        setState({ status: "result", data, error: null, httpStatus: null });
      })
      .catch((error) => {
        if (controller.signal.aborted || id !== requestIdRef.current) return;
        setState((prev) => ({
          status: "error",
          data: prev.data,
          error: error.message,
          httpStatus: error.status ?? null,
        }));
      });

    return () => controller.abort();
  }, [line, period, retryToken]);

  return { ...state, retry: () => setRetryToken((n) => n + 1) };
}
