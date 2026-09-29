// Loading placeholder primitive. Decorative only (aria-hidden): the surrounding region
// carries aria-busy and the visually-hidden status text, so screen readers hear one message
// instead of a run of empty blocks.
export default function Skeleton({ variant = "block", width, height, className = "", style }) {
  return (
    <span
      className={`skeleton skeleton-${variant}${className ? ` ${className}` : ""}`}
      style={{ width, height, ...style }}
      aria-hidden="true"
    />
  );
}
