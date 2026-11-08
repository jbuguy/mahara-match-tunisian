import { geoMercator, geoPath } from "d3-geo";
import { useEffect, useMemo, useState } from "react";
import type { Geometry } from "geojson";
import { metricColorClass, metricValue, METRIC_BREAKPOINTS } from "./governorateMapUtils";
import type { GovernorateMetric } from "./governorateMapUtils";

type GovernorateRow = {
  code: string;
  name_fr: string;
  name_ar: string;
  candidates: { value: number | null; suppressed?: boolean };
  open_positions: { value: number | null; suppressed?: boolean };
  published_courses: { value: number | null; suppressed?: boolean };
  candidates_per_open_position: { value: number | null; reason?: string };
};

type Feature = { type: "Feature"; properties: { governorate_code: string; name_fr: string; name_ar: string }; geometry: Geometry };
type FeatureCollection = { type: "FeatureCollection"; features: Feature[] };

const METRICS: Array<[GovernorateMetric, string]> = [
  ["candidates", "Candidats"],
  ["open_positions", "Postes ouverts"],
  ["published_courses", "Formations"],
  ["candidates_per_open_position", "Candidats par poste"],
];

const COLORS = ["#edf7f5", "#b8ddd7", "#6eb8ae", "#2d8980", "#075b54"];

export function GovernorateMap({
  metric = "candidates_per_open_position",
  data,
  onSelect,
  meta,
}: {
  metric?: GovernorateMetric;
  data?: GovernorateRow[];
  onSelect: (code: string) => void;
  meta?: { source?: string; period?: object; methodology?: string; retrieved_at?: string };
}) {
  const [geojson, setGeojson] = useState<FeatureCollection | null>(null);
  const [selectedMetric, setSelectedMetric] = useState(metric);
  const [table, setTable] = useState(false);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);
  const rows = data ?? [];
  useEffect(() => {
    fetch("/data/tunisia-governorates.geojson").then((response) => response.json()).then(setGeojson).catch(() => setGeojson(null));
  }, []);

  const path = useMemo(() => {
    if (!geojson) return null;
    const projection = geoMercator().fitExtent([[20, 20], [580, 500]], geojson);
    return geoPath(projection);
  }, [geojson]);

  const rowByCode = useMemo(() => new Map(rows.map((row) => [row.code, row])), [rows]);
  const valueFor = (code: string) => metricValue(rowByCode.get(code) ?? {}, selectedMetric);
  const suppressed = (code: string) => {
    const row = rowByCode.get(code);
    const cell = row?.[selectedMetric] as { suppressed?: boolean } | undefined;
    return Boolean(cell?.suppressed || (row?.[selectedMetric] as { value?: number })?.value === null && selectedMetric !== "candidates_per_open_position");
  };
  const accessibleText = (row: GovernorateRow) =>
    `${row.name_fr}, ${row.name_ar || ""}. ${METRICS.find(([key]) => key === selectedMetric)?.[1]}: ${valueFor(row.code) ?? "non disponible"}; candidats: ${(row.candidates as { value: number }).value ?? "masqué"}; postes ouverts: ${(row.open_positions as { value: number }).value ?? "masqué"}; formations: ${(row.published_courses as { value: number }).value ?? "masqué"}.`;

  const exportCsv = () => {
    const csv = ["code,gouvernorat,candidats,postes ouverts,formations,candidats par poste", ...rows.map((row) =>
      [row.code, row.name_fr, (row.candidates as { value: number }).value ?? "", (row.open_positions as { value: number }).value ?? "", (row.published_courses as { value: number }).value ?? "", (row.candidates_per_open_position as { value?: number }).value ?? ""].join(",")
    )].join("\n");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    link.download = "gouvernorats.csv";
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const priority = [...rows].sort((a, b) => {
    const ratioA = (a.candidates_per_open_position as { value?: number }).value ?? -1;
    const ratioB = (b.candidates_per_open_position as { value?: number }).value ?? -1;
    const courseA = (a.published_courses as { value?: number }).value ?? 0;
    const courseB = (b.published_courses as { value?: number }).value ?? 0;
    return ratioB - ratioA || courseA - courseB;
  }).slice(0, 3);

  return (
    <section className="governorate-map">
      <div className="governorate-map-switcher" role="group" aria-label="Indicateur cartographique">
        {METRICS.map(([key, label]) => <button key={key} type="button" aria-pressed={selectedMetric === key} onClick={() => setSelectedMetric(key)}>{label}</button>)}
      </div>
      <div className="governorate-map-layout">
        <div>
          {!table && geojson && path ? <svg viewBox="0 0 620 520" role="img" aria-label="Carte des gouvernorats tunisiens">
            <defs><pattern id="suppressed-hatch" width="6" height="6" patternUnits="userSpaceOnUse"><path d="M0 6L6 0" stroke="#777" strokeWidth="1" /></pattern></defs>
            {geojson.features.map((feature) => {
              const code = feature.properties.governorate_code;
              const row = rowByCode.get(code);
              const noPositions = selectedMetric === "candidates_per_open_position" && row?.candidates_per_open_position.reason === "no_open_positions";
              const fill = noPositions ? "#d5d5d5" : suppressed(code) ? "url(#suppressed-hatch)" : COLORS[metricColorClass(selectedMetric, valueFor(code))];
              return <path key={code} d={path(feature) ?? undefined} fill={fill} className="governorate-map-path"
                tabIndex={0} role="button"
                aria-label={row ? accessibleText(row) : `${feature.properties.name_fr}: donnée indisponible`}
                onMouseMove={(event) => setTooltip({ x: event.clientX, y: event.clientY, text: row ? accessibleText(row) : feature.properties.name_fr })}
                onMouseLeave={() => setTooltip(null)}
                onFocus={() => setTooltip({ x: 0, y: 0, text: row ? accessibleText(row) : feature.properties.name_fr })}
                onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(code); } }}
                onClick={() => onSelect(code)} />;
            })}
          </svg> : null}
          {table ? <table>
            <thead><tr><th>Gouvernorat</th><th>Candidats</th><th>Postes</th><th>Formations</th><th>Candidats/poste</th></tr></thead>
            <tbody>{rows.map((row) => <tr key={row.code}><th>{row.name_fr}</th><td>{(row.candidates as { value: number }).value ?? "-"}</td><td>{(row.open_positions as { value: number }).value ?? "-"}</td><td>{(row.published_courses as { value: number }).value ?? "-"}</td><td>{(row.candidates_per_open_position as { value?: number }).value ?? "-"}</td></tr>)}</tbody>
          </table> : null}
          <button type="button" onClick={() => setTable((value) => !value)}>{table ? "Afficher la carte" : "Afficher en tableau"}</button>
          {table ? <button type="button" onClick={exportCsv}>Exporter en CSV</button> : null}
          <div className="map-legend" aria-label="Légende">
            {COLORS.map((color, index) => <span key={color}><i style={{ background: color }} /> {METRIC_BREAKPOINTS[selectedMetric][index] ?? "+"}</span>)}
            <span><i className="hatched" /> masqué (&lt;5 personnes)</span>
            <span><i style={{ background: "#d5d5d5" }} /> pas d'offres</span>
          </div>
        </div>
        <aside>
          <h3>Gouvernorats à renforcer en priorité</h3>
          <ol>{priority.map((row) => <li key={row.code}><button type="button" onClick={() => onSelect(row.code)}>{row.name_fr}</button></li>)}</ol>
        </aside>
      </div>
      <footer className="map-source">
        Source : {meta?.source ?? "Mahara Match platform"} · {String(meta?.period ?? "")} · {meta?.methodology} · récupéré le {meta?.retrieved_at}
        <div>Limites administratives : geoBoundaries TUN ADM1, ODbL 1.0 ; © OpenStreetMap contributors.</div>
      </footer>
      {tooltip ? <div role="tooltip" className="map-tooltip">{tooltip.text}</div> : null}
    </section>
  );
}
