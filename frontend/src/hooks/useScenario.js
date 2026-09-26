import { useEffect, useRef, useState } from "react";

import { runScenario } from "../api/client.js";

const DEBOUNCE_MS = 250;

// Debounces scenario changes, discards stale/out-of-order responses, and keeps the
// previous result visible (dimmed by the caller via status "updating") while a new one
// loads — the UI never unmounts while waiting for the API. `httpStatus` lets callers show
// a specific "model unavailable" message for a 503 (POST /scenario) without re-parsing
// `error`. `retry()` re-issues the same request (e.g. after a network error).
export function useScenario(scenarioParams) {
  const [state, setState] = useState({ status: "loading", result: null, error: null, httpStatus: null });
  const [retryToken, setRetryToken] = useState(0);
  const requestIdRef = useRef(0);
  const paramsKey = JSON.stringify(scenarioParams);

  useEffect(() => {
    if (scenarioParams == null) return undefined;
    const id = ++requestIdRef.current;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setState((prev) => ({
        status: prev.result ? "updating" : "loading",
        result: prev.result,
        error: null,
        httpStatus: null,
      }));
      runScenario(scenarioParams, { signal: controller.signal })
        .then((result) => {
          if (id !== requestIdRef.current) return;
          setState({ status: "result", result, error: null, httpStatus: null });
        })
        .catch((error) => {
          if (controller.signal.aborted || id !== requestIdRef.current) return;
          setState((prev) => ({
            status: "error",
            result: prev.result,
            error: error.message,
            httpStatus: error.status ?? null,
          }));
        });
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey, retryToken]);

  return { ...state, retry: () => setRetryToken((n) => n + 1) };
}
