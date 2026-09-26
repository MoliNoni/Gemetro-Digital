// Mode switch (G-01): guided mode is the default view; simulation mode is the previous
// free-parameter simulator, kept as an "advanced" mode. A plain button group, not a
// dropdown, so both modes and the current one are visible without interaction.
export default function ModeSwitch({ mode, onChange }) {
  return (
    <div className="mode-switch" role="group" aria-label="Modo del simulador">
      <button
        type="button"
        className={`mode-button${mode === "guided" ? " is-selected" : ""}`}
        aria-pressed={mode === "guided"}
        onClick={() => onChange("guided")}
      >
        Modo guiado
      </button>
      <button
        type="button"
        className={`mode-button${mode === "simulation" ? " is-selected" : ""}`}
        aria-pressed={mode === "simulation"}
        onClick={() => onChange("simulation")}
      >
        Modo simulación
      </button>
    </div>
  );
}
