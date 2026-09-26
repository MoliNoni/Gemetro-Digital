// Spanish glossary shown by InfoTooltip next to technical terms in the UI (F-02).
// Conceptual only, by direction's constraint: no numeric bound, no invented fact, and no
// confidence/probability/accuracy/F1/"precisión estimada" wording. When a fact is not
// clearly established in the project docs, the text stays generic rather than guessing.
//
// Feedback round 2 (direction 2026-09-25, point 7): every entry is worded to lead with the
// variable's name, not its symbol — the symbol only follows in parentheses, as a reference,
// never as the label itself.

export const GLOSSARY = {
  pmv:
    "PMV (Voto Medio Predicho): un índice normativo de confort térmico que combina " +
    "temperatura, humedad, velocidad del aire, tasa metabólica y aislamiento de la ropa " +
    "en un solo valor.",
  iso7730:
    "ISO 7730 es la norma internacional que define el cálculo del PMV y los rangos de " +
    "entrada y de resultado que reconoce como válidos.",
  mlDomain:
    "El modelo de aprendizaje automático (ML) fue entrenado con encuestas reales " +
    "recogidas en vagones del metro de Nanjing. Sus predicciones corresponden al " +
    "comportamiento observado en esas condiciones de entrenamiento; fuera de ellas, el " +
    "modelo extrapola.",
  extrapolation:
    "Cuando un escenario se aleja de las condiciones observadas en el entrenamiento, o de " +
    "los rangos que reconoce una norma, el modelo o la fórmula está extrapolando: el " +
    "resultado se sigue mostrando, pero como un estado informativo, no como un error.",
  phiPeak:
    "La ocupación en la hora pico fija qué tan lleno está el vagón en el momento " +
    "de mayor demanda del día. El resto de las horas se escala a partir de ese valor con el " +
    "perfil horario de la línea.",
  tauR:
    "El tiempo de renovación de aire resume qué tan rápido se intercambia el aire del " +
    "vagón con el exterior. Es la fuente de incertidumbre que más afecta el resultado del " +
    "simulador.",
  vel:
    "Velocidad del aire percibida por un pasajero dentro del vagón; es una de las entradas " +
    "del PMV y del modelo ML.",
  clo:
    "Aislamiento térmico de la ropa, en unidades clo; es una de las entradas del PMV y del " +
    "modelo ML.",
  deltaT:
    "La diferencia de temperatura interior–exterior es el aumento de temperatura " +
    "interior sobre la temperatura exterior. El modo avanzado permite fijarla directamente " +
    "en lugar de derivarla del tiempo de renovación de aire.",
  n:
    "El número de pasajeros estimado dentro del vagón se calcula, para el escenario " +
    "elegido, a partir de la ocupación de la línea y de la ocupación en hora pico. No se " +
    "puede fijar directamente.",
  rhLimit:
    "La humedad relativa interior tiene un límite físico que no puede superarse. Cuando el " +
    "cálculo lo alcanza, el valor se recorta a ese límite y el resultado queda marcado " +
    "como tal.",
  simulatorValidity:
    "El simulador térmico se basa en una fórmula con un rango de validez reconocido. Fuera " +
    "de ese rango, el resultado se marca como fuera de validez del simulador en lugar de " +
    "descartarse.",
};

// Line selector tooltip (feedback round 2, point 12): rewritten from data. Verified against
// artifacts/occupancy_shape.csv — line A's occupancy shape peaks (load_ratio 1.0) at 16 h,
// line B's at 17 h; both lines feed the same thermal/PMV/ML chain (src/gemetro/scenario.py),
// only the occupancy shape differs per line.
export const LINE_TOOLTIP =
  "Las líneas A y B usan el mismo modelo térmico; solo cambia el perfil horario de " +
  "ocupación, derivado de las entradas reales de cada línea por tren. En la línea A la " +
  "carga máxima es a las 16 h y en la línea B a las 17 h, por eso el escenario se separa " +
  "por línea.";

// Short, code/ISO-backed effect examples for the simulation mode's advanced controls
// (feedback round 2, point 13). Each one is traceable to a specific equation/table so no
// new claim is introduced: simulator.py equations 4-5 (τr -> mass flow -> ΔT -> Tin),
// pmv.py:54-59 (hc from vel) and :110 (met from posture), occupancy.py:32-34 (φ_pico -> N).
// Never claims an effect on the ML class: that relationship is empirical, not derivable
// from a formula.
export const EFFECT_EXAMPLES = {
  phiPeak:
    "Ejemplo: más ocupación en hora pico → más pasajeros → más calor interno → sube la " +
    "temperatura interior.",
  vel:
    "Ejemplo: más velocidad del aire → más pérdida de calor por convección → baja el PMV " +
    "(sensación más fresca). No cambia la temperatura interior simulada.",
  clo:
    "Ejemplo: más aislamiento → menos pérdida de calor del cuerpo → sube el PMV (sensación " +
    "más cálida).",
  posture:
    "Ejemplo: de pie (1,2 met) genera más calor metabólico que sentado (1,0 met) → el PMV " +
    "sube.",
  tauR:
    "Ejemplo: más tiempo de renovación → menos aire exterior por segundo → sube la " +
    "temperatura interior.",
};
