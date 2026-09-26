// Sources shown in the page footer (feedback round 4, direction 2026-09-26). Only sources the
// project actually uses; every entry is taken from DATA_SOURCES.md / README.md
// ("Fuentes y atribución") — nothing here is new or unverified. Grouped by what each source
// feeds: the ML training data, the Medellín scenario inputs, the thermal simulator's
// constants, the normative baseline and the external reference drawn on the τr chart.

export const REPOSITORY_URL = "https://github.com/MoliNoni";

export const SOURCE_GROUPS = [
  {
    title: "Modelo de confort (entrenamiento y evaluación)",
    items: [
      {
        // Download link supplied by the direction (2026-09-26) as the one published with the
        // Nanjing study; see DATA_SOURCES.md S-09 addendum.
        text: "Encuestas de sensación térmica y mediciones en vagones del metro de Nanjing (junio–julio de 2025), publicadas por los autores del estudio en Baidu Netdisk (código de extracción 4d84).",
        url: "https://pan.baidu.com/s/1o3wor2rxNiptwnvJ2fthag?pwd=4d84",
      },
      {
        text: "Estudio: Zhang, Li, Chen. Índice adimensional de confort térmico para sistemas de metro, validado en la red de Nanjing. Journal of Building Physics, 2026.",
        url: "https://doi.org/10.1177/17442591261474106",
      },
    ],
  },
  {
    title: "Clima de Medellín",
    items: [
      {
        text: "IDEAM, estación Olaya Herrera: temperatura y humedad del aire (datos.gov.co, sbwg-7ju4 y uext-mhny, CC BY-SA 4.0).",
        url: "https://www.datos.gov.co/resource/sbwg-7ju4.json",
      },
      {
        text: "IDEAM: presión atmosférica (62tk-nxj5) y Catálogo Nacional de Estaciones (hp9r-jxuu).",
        url: "https://www.datos.gov.co/resource/62tk-nxj5.json",
      },
    ],
  },
  {
    title: "Ocupación y operación del Metro de Medellín",
    items: [
      {
        text: "Metro de Medellín, datos abiertos: afluencia 2025 y GTFS 2025 (licencia no declarada; se cita la fuente).",
        url: "https://datosabiertos-metrodemedellin.opendata.arcgis.com/",
      },
      {
        text: "Metro de Medellín, ficha oficial de la línea A: capacidad de 300 usuarios por vagón.",
        url: "https://www.metrodemedellin.gov.co/en/users/integrated-system/line-a",
      },
      {
        text: "Wikipedia: dimensiones de los vagones de las líneas A y B (fuente secundaria).",
        url: "https://es.wikipedia.org/wiki/Anexo:Veh%C3%ADculos_del_sistema_de_transporte_masivo_del_Valle_de_Aburra",
      },
    ],
  },
  {
    title: "Simulador y confort normativo",
    items: [
      {
        text: "ASHRAE Handbook — Fundamentals (2013): calor sensible y latente de los ocupantes (vía reproducción de CED Engineering).",
        url: "https://www.cedengineering.com/userfiles/M06-004%20-%20Cooling%20Load%20Calculations%20and%20Principles%20-%20US.pdf",
      },
      { text: "ISO 7730: índice PMV (baseline normativo)." },
    ],
  },
  {
    title: "Referencia externa",
    items: [
      {
        text: "Metro de Praga, línea C: microclima en vagón (Applied Sciences 2026, 16, 7161, CC BY 4.0) — línea de referencia del gráfico de renovación de aire.",
        url: "https://doi.org/10.3390/app16147161",
      },
    ],
  },
];
