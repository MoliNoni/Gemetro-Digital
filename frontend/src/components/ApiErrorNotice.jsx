// Shared error presentation for API calls (G-02): a 503 ("model not loaded", both
// /scenario and /guided) always reads "Modelo no disponible" instead of the raw detail
// text, so a backend restart doesn't look like an arbitrary error. Any other failure
// (network, unexpected response) shows the message as received. This is a real failure, not
// an extrapolation/out-of-range state, so it keeps the "error" (red) style, never "warn".
export default function ApiErrorNotice({ error, httpStatus, onRetry }) {
  const modelUnavailable = httpStatus === 503;
  return (
    <p role="alert" className="error">
      {modelUnavailable ? "Modelo no disponible" : `Error: ${error}`}
      {onRetry && (
        <>
          {" "}
          <button type="button" className="retry-button" onClick={onRetry}>
            Reintentar
          </button>
        </>
      )}
    </p>
  );
}
