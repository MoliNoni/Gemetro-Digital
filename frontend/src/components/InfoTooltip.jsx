import { useId, useState } from "react";

// Reusable contextual explanation, reachable by mouse (hover) and by keyboard (focus),
// with no external library. The trigger is a real <button> so it is reachable without a
// mouse; the tooltip node stays mounted at all times (so `aria-describedby` always points
// at a real element) and only its visibility toggles, via an inline style so it is testable
// independently of whether the stylesheet is loaded.
export default function InfoTooltip({ text, glyph = "?", label = "Más información", className = "" }) {
  const [open, setOpen] = useState(false);
  const id = useId();

  const show = () => setOpen(true);
  const hide = () => setOpen(false);

  return (
    <span className={`info-tooltip ${className}`.trim()}>
      <button
        type="button"
        className="info-tooltip-trigger"
        aria-describedby={id}
        aria-label={label}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
      >
        {glyph}
      </button>
      <span
        role="tooltip"
        id={id}
        className="info-tooltip-bubble"
        style={{ display: open ? "block" : "none" }}
      >
        {text}
      </span>
    </span>
  );
}
