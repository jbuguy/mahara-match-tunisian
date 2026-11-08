import { useEffect, useMemo, useState } from "react";
import { fetchObservatory, logObservatoryExport } from "../auth";
import { GovernorateMap } from "./GovernorateMap";

type Props = { token: string };
type Metric = { value: number | null; previous?: number | null; delta?: number | null; sparkline?: number[] };
const METRIC_KEYS = ["active_candidates", "open_positions", "declared_placement_rate", "median_days_to_hire", "youth_share_of_candidates", "training_to_job_rate"] as const;
const KPI_LABELS = ["Candidats actifs", "Postes ouverts", "Taux de placement déclaré", "Délai médian d’embauche", "Jeunes 15–24 ans", "Taux formation → emploi"];
const KPI_DEFINITIONS = [
  "Candidats ayant postulé ou mis à jour leur profil.",
  "Postes publiés dans les offres non expirées.",
  "Embauches sur les candidatures clôturées.",
  "Délai médian entre candidature et embauche.",
  "Part des candidats âgés de 15 à 24 ans.",
  "Diplômés ayant trouvé un emploi sous 90 jours.",
];

function unwrap(value: unknown): number | string | null {
  if (typeof value === "number" || typeof value === "string") return value;
  if (value && typeof value === "object" && "value" in value) {
    const result = (value as { value?: unknown }).value;
    return typeof result === "number" ? result : result == null ? "—" : String(result);
  }
  return null;
}

function Card({ title, question, footer, children, className = "", onExport }: { title?: string; question?: string; footer?: string; children: React.ReactNode; className?: string; onExport?: () => void }) {
  return <article className={`observatory-card ${className}`}>
    {title && <><div className="observatory-card__heading"><h3>{title}</h3>{onExport && <button type="button" className="chart-export" onClick={onExport} aria-label={`Exporter ${title} en CSV`}>CSV</button>}</div>{question && <p className="observatory-card__question">{question}</p>}</>}
    <div className="observatory-card__body">{children}</div>
    {footer && <footer className="observatory-card__footer">{footer}</footer>}
  </article>;
}

function Status({ children }: { children: React.ReactNode }) { return <span className="status-badge">✓ {children}</span>; }

function csvCell(value: unknown): string {
  if (value && typeof value === "object") {
    const privacy = value as { value?: unknown; suppressed?: boolean };
    if (privacy.suppressed && privacy.value == null) return "<5";
    if ("value" in privacy) return csvCell(privacy.value);
  }
  return value == null ? "" : String(value);
}

function flattenRows(value: unknown, rows: Record<string, unknown>[] = [], prefix = ""): Record<string, unknown>[] {
  if (Array.isArray(value)) {
    value.forEach((item) => {
      if (item && typeof item === "object" && !Array.isArray(item)) rows.push(Object.fromEntries(Object.entries(item).map(([key, cell]) => [`${prefix}${key}`, cell])));
      else rows.push({ [`${prefix}value`]: item });
    });
    return rows;
  }
  if (value && typeof value === "object") {
    const entries = Object.entries(value);
    if (entries.every(([, item]) => typeof item !== "object" || item === null)) rows.push(Object.fromEntries(entries.map(([key, cell]) => [`${prefix}${key}`, cell])));
    else entries.forEach(([key, item]) => flattenRows(item, rows, `${prefix}${key}.`));
  } else rows.push({ [`${prefix || "value"}`]: value });
  return rows;
}

function downloadCsv(filename: string, response: unknown, filters: Record<string, string>) {
  const data = response as { meta?: Record<string, unknown>; rows?: unknown };
  const period = (data.meta?.period as { start_date?: string; end_date?: string } | undefined) ?? {};
  const activeFilters = Object.entries(filters).filter(([, value]) => value).map(([key, value]) => `${key}=${value}`).join("; ");
  const displayed = data.rows ?? Object.fromEntries(Object.entries(data).filter(([key]) => key !== "meta"));
  const rows = flattenRows(displayed);
  const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  const csvRows = [
    ["source", csvCell(data.meta?.source ?? "")],
    ["period", `${period.start_date ?? ""} - ${period.end_date ?? ""}`],
    ["methodology", csvCell(data.meta?.methodology ?? "")],
    ["retrieved_at", csvCell(data.meta?.retrieved_at ?? "")],
    ["active_filters", activeFilters],
    [],
    columns,
    ...rows.map((row) => columns.map((column) => csvCell(row[column]))),
  ];
  const csv = csvRows.map((row) => row.map((cell) => `"${String(cell ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

function Sparkline({ values }: { values: number[] }) {
  const safe = values.length ? values : [0];
  const max = Math.max(...safe, 1);
  const min = Math.min(...safe);
  const range = Math.max(max - min, 1);
  const points = safe.map((value, index) => `${safe.length === 1 ? 50 : index / (safe.length - 1) * 100},${30 - (value - min) / range * 22}`).join(" ");
  return <svg className="kpi-sparkline" viewBox="0 0 100 32" role="img" aria-label="Évolution sur douze points"><polyline points={points} /></svg>;
}

function nationalLinePath(series: any[], maxValue: number) {
  if (!series.length) return "";
  const width = 560;
  const height = 180;
  return series.map((point, index) => {
    const x = series.length === 1 ? width / 2 : index / (series.length - 1) * width;
    const y = height - (Number(point.value ?? 0) / Math.max(maxValue, 1)) * (height - 16);
    return `${index ? "L" : "M"} ${x} ${y}`;
  }).join(" ");
}

export function AdminObservatoryDashboard({ token }: Props) {
  const [filters, setFilters] = useState({ startDate: "", endDate: "", governorateCode: "", sectorCode: "", ageGroup: "" });
  const [youth, setYouth] = useState(false);
  const [showAllYouth, setShowAllYouth] = useState(false);
  const [responses, setResponses] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const endpoints = ["kpis", "national-context", "funnel", "time-to-hire", "governorates", "youth-by-governorate", "skills-gap", "training-alignment", "employers-quality"];

  const load = () => {
    endpoints.forEach((endpoint) => {
      fetchObservatory(token, endpoint, endpoint === "funnel" ? { ...filters, youth } : filters)
        .then((result) => setResponses((current) => ({ ...current, [endpoint]: result })))
        .catch(() => setErrors((current) => ({ ...current, [endpoint]: "Indicateurs indisponibles pour le moment." })));
    });
  };
  useEffect(load, [token, filters.startDate, filters.endDate, filters.governorateCode, filters.sectorCode, filters.ageGroup, youth]);

  const kpis = responses.kpis as Record<string, Metric> | undefined;
  const national = responses["national-context"] as any;
  const funnel = responses.funnel as any;
  const timing = responses["time-to-hire"] as any;
  const governorates = responses.governorates as any;
  const youthGovernorates = responses["youth-by-governorate"] as any;
  const skills = responses["skills-gap"] as any;
  const training = responses["training-alignment"] as any;
  const quality = responses["employers-quality"] as any;
  const monthlyApplications = Array.isArray(national?.platform?.applications)
    ? national.platform.applications
    : Array.isArray(national?.platform?.applications?.series)
      ? national.platform.applications.series
      : [];
  const employmentSeries = Array.isArray(national?.national?.employment_to_population?.series)
    ? national.national.employment_to_population.series
    : [];
  const agriculturalJobs = Array.isArray(national?.national?.agridata_jobs_created?.series)
    ? national.national.agridata_jobs_created.series
    : [];
  const totalUnemployment = Array.isArray(national?.national?.total_unemployment?.series)
    ? national.national.total_unemployment.series
    : [];
  const youthUnemployment = Array.isArray(national?.national?.youth_unemployment_15_24?.series)
    ? national.national.youth_unemployment_15_24.series
    : [];

  const funnelRows = useMemo(() => {
    const labels: Record<string, string> = { registered: "Inscrits", profile_completed: "Profil complété", applied: "Ont postulé", shortlisted: "Présélectionnés", interviewed: "Entretiens", offered: "Offres reçues", hired: "Embauchés (déclaré)" };
    return Object.entries(funnel?.counts ?? {}).map(([key, value]) => ({ key, label: labels[key] ?? key, count: unwrap(value) }));
  }, [funnel]);
  const maxFunnel = Math.max(1, ...funnelRows.map((row) => Number(row.count) || 0));
  const funnelDrop = funnelRows.slice(1).map((row, index) => {
    const previous = Number(funnelRows[index].count) || 0;
    const current = Number(row.count) || 0;
    return { from: funnelRows[index].label, to: row.label, drop: previous - current };
  }).sort((left, right) => right.drop - left.drop)[0];

  const medianDays = unwrap(timing?.median_days);
  const histogramBins = Array.isArray(timing?.histogram)
    ? timing.histogram
    : Object.entries(timing?.histogram ?? {}).map(([bin, value]) => ({ bin, value }));
  const histogramValues = histogramBins.map((item: any) => Number(unwrap(item.value ?? item.count)) || 0);
  const medianPosition = Math.max(0, Math.min(92, ((Number(medianDays) || 0) / 60) * 92));
  const governorateOptions = Array.isArray(governorates?.rows) ? governorates.rows.filter((row: any) => row.code !== "unspecified") : [];
  const activeFilters = {
    start_date: filters.startDate,
    end_date: filters.endDate,
    governorate_code: filters.governorateCode,
    sector_code: filters.sectorCode,
    age_group: filters.ageGroup,
  };

  const exportCsv = () => {
    const rows: string[][] = [["section", "endpoint", "data"]];
    Object.entries(responses).forEach(([endpoint, value]) => rows.push([endpoint, endpoint, JSON.stringify(value)]));
    const csv = rows.map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "observatoire.csv";
    link.click();
    URL.revokeObjectURL(link.href);
    void logObservatoryExport(token, { export_type: "csv", section: "dashboard", filters: activeFilters });
  };

  const setPeriod = (preset: string) => {
    const end = new Date();
    if (!preset) {
      setFilters((current) => ({ ...current, startDate: "", endDate: "" }));
      return;
    }
    const months = preset === "12-months" ? 12 : preset === "3-months" ? 3 : 6;
    const start = new Date(end);
    start.setMonth(start.getMonth() - months);
    setFilters((current) => ({
      ...current,
      startDate: start.toISOString().slice(0, 10),
      endDate: end.toISOString().slice(0, 10),
    }));
  };

  const exportChart = (filename: string, endpoint: string, chart: string) => {
    const response = responses[endpoint];
    if (!response) return;
    downloadCsv(filename, response, activeFilters);
    void logObservatoryExport(token, { export_type: "csv", chart, filters: activeFilters });
  };

  const exportPdf = () => {
    void logObservatoryExport(token, { export_type: "pdf", section: "dashboard", filters: activeFilters }).finally(() => window.print());
  };

  return <main className="observatory-page">
    <header className="observatory-header">
      <div><div className="observatory-eyebrow">OBSERVATOIRE DE L’EMPLOI · MAHARA MATCH</div><h1>Tableau de bord du ministère</h1>
      <p>Le marché du travail évolue-t-il ? La plateforme aide-t-elle vraiment à trouver un emploi ? Où faut-il agir ? Données agrégées, aucun profil individuel.</p></div>
      <div className="observatory-actions"><button className="button button-secondary" onClick={exportCsv}>Exporter les données (CSV)</button><button className="button button-primary" onClick={exportPdf}>Exporter le tableau de bord (PDF)</button></div>
    </header>

    <section className="observatory-filter-card" aria-label="Filtres du tableau de bord">
      <label>Période<select defaultValue="" onChange={(event) => setPeriod(event.target.value)}><option value="">Toute la période</option><option value="3-months">3 derniers mois</option><option value="6-months">6 derniers mois</option><option value="12-months">12 derniers mois</option></select></label>
      <label>Gouvernorat<select value={filters.governorateCode} onChange={(event) => setFilters((current) => ({ ...current, governorateCode: event.target.value }))}><option value="">Tous</option>{governorateOptions.map((row: any) => <option key={row.code} value={row.code}>{row.name_fr}</option>)}</select></label>
      <label>Secteur<select value={filters.sectorCode} onChange={(event) => setFilters((current) => ({ ...current, sectorCode: event.target.value }))}><option value="">Tous</option></select></label>
      <label>Tranche d’âge<select value={filters.ageGroup} onChange={(event) => setFilters((current) => ({ ...current, ageGroup: event.target.value }))}><option value="">Toutes</option><option value="15-24">15–24</option><option value="25-34">25–34</option><option value="35+">35+</option></select></label>
      <p>Comparaison automatique avec la période précédente. Tout chiffre inférieur à 5 personnes est masqué (&lt;5).</p>
    </section>
    <div className="observatory-print-filters" aria-hidden="true">
      <strong>Filtres sélectionnés</strong>
      <span>Période : {filters.startDate || filters.endDate ? `${filters.startDate || "début"} – ${filters.endDate || "fin"}` : "Toute la période"}</span>
      <span>Gouvernorat : {governorateOptions.find((row: any) => row.code === filters.governorateCode)?.name_fr ?? "Tous"}</span>
      <span>Secteur : {filters.sectorCode || "Tous"}</span>
      <span>Âge : {filters.ageGroup || "Toutes les tranches"}</span>
    </div>

    <section className="observatory-kpis" aria-label="Indicateurs clés">
      {METRIC_KEYS.map((key, index) => {
        const metric = kpis?.[key];
        const delta = typeof metric?.delta === "number" ? metric.delta : null;
        return <Card key={key} className="kpi-card" footer={kpis?.meta ? "Mahara Match · indicateurs agrégés" : undefined}>
          <span className="kpi-card__label">{KPI_LABELS[index]}</span>
          <strong className="kpi-card__value">{metric ? unwrap(metric.value) ?? "—" : errors.kpis ? "Erreur" : "…"}{key.includes("share") || key.includes("rate") ? "%" : ""}</strong>
          {delta !== null && <span className={delta >= 0 ? "delta-positive" : "delta-negative"}>{delta >= 0 ? "▲" : "▼"} {Math.abs(delta)}% vs période précédente</span>}
          {metric?.sparkline && <Sparkline values={metric.sparkline.map(Number)} />}
          <p>{KPI_DEFINITIONS[index]}</p>
        </Card>;
      })}
    </section>

    <div className="observatory-section-title"><span>1 · L’IMPACT DU TRAVAIL</span><h2>Le marché du travail : que fait-il en Tunisie ?</h2></div>
    <section className="observatory-grid observatory-grid--market">
      <Card title="Chômage et activité" question="Quel est le mouvement du chômage total et des jeunes ?" footer={`Sources : ${national?.meta?.source ?? "Banque mondiale · AgriData · Mahara Match"}`} onExport={() => exportChart("contexte-national.csv", "national-context", "chômage et activité")}>
        {national ? <div className="simple-line-chart" aria-label="Séries nationales">
          <svg viewBox="0 0 560 180" role="img" aria-label="Évolution du chômage total et du chômage des jeunes">
            <path className="national-line national-line--total" d={nationalLinePath(totalUnemployment, Math.max(...totalUnemployment.map((row: any) => Number(row.value ?? 0)), ...youthUnemployment.map((row: any) => Number(row.value ?? 0)), 1))} />
            <path className="national-line national-line--youth" d={nationalLinePath(youthUnemployment, Math.max(...totalUnemployment.map((row: any) => Number(row.value ?? 0)), ...youthUnemployment.map((row: any) => Number(row.value ?? 0)), 1))} />
          </svg>
          <div className="chart-direct-label youth">Jeunes 15–24 ans</div><div className="chart-direct-label total">Population active</div>
        </div> : <div className="loading-state">Chargement…</div>}
        <h4>Activité de la plateforme : candidatures par mois</h4>
        <div className="monthly-bars">{monthlyApplications.map((item: any, index: number) => <i key={index} style={{ height: `${Math.max(8, Number(item.value ?? 0) / Math.max(1, ...monthlyApplications.map((row: any) => Number(row.value ?? 0))) * 100)}%` }} title={`${item.month ?? item.year ?? ""}: ${item.value}`} />)}</div>
      </Card>
      <div className="observatory-stack">
        <Card title="Emploi / population" question="Mesure de participation au marché du travail" footer={`Source : ${national?.national?.employment_to_population?.source ?? "Banque mondiale"}`}><strong className="big-stat">{employmentSeries.length ? `${employmentSeries.at(-1)?.value ?? "—"} %` : "—"}</strong><p>Mesure de participation, pas un nombre d’offres.</p></Card>
        <Card title="Emplois liés à l’investissement agricole" question="Emplois projetés par les investissements déclarés" footer={`Source : ${national?.national?.agridata_jobs_created?.source ?? "AgriData"}`}><strong className="big-stat">{agriculturalJobs.length ? agriculturalJobs.at(-1)?.value ?? "—" : "—"}</strong><div className="mini-year-bars">{agriculturalJobs.slice(-5).map((item: any) => <i key={item.year} style={{ height: `${Math.max(6, Number(item.value ?? 0) / Math.max(1, ...agriculturalJobs.map((row: any) => Number(row.value ?? 0))) * 46)}px` }} title={`${item.year} : ${item.value}`} />)}</div><p>Emplois attribués à des projets, pas des offres ni l’emploi total.</p></Card>
      </div>
    </section>

    <div className="observatory-section-title"><span>2 · IMPACT DE LA PLATEFORME</span><h2>La plateforme aide-t-elle réellement à trouver un emploi ?</h2></div>
    <section className="observatory-grid observatory-grid--impact">
      <Card title="Du compte à l’embauche" question="Parcours des candidats dans la plateforme" footer={funnel?.meta?.source ?? "Mahara Match"} onExport={() => exportChart("funnel-candidats.csv", "funnel", "funnel")}>
        <div className="segmented"><button className={!youth ? "active" : ""} onClick={() => setYouth(false)}>Tous</button><button className={youth ? "active" : ""} onClick={() => setYouth(true)}>Jeunes 15–24</button></div>
        <div className="funnel">{funnelRows.map((row) => <div className="funnel-row" key={row.key}><span>{row.label}</span><div><i style={{ width: `${Number(row.count) / maxFunnel * 100}%` }} /></div><strong>{row.count}</strong></div>)}</div>
        <p className="reading">Lecture : {funnelDrop && funnelDrop.drop > 0 ? `La plus forte baisse se situe entre ${funnelDrop.from} et ${funnelDrop.to} (${funnelDrop.drop} personnes).` : "Aucune baisse significative n’est observable entre les étapes disponibles."}</p>
      </Card>
      <div className="observatory-stack">
        <Card title="Rapidité d’embauche" question="Nombre de jours entre candidature et embauche" footer={timing?.meta?.source ?? "Historique des statuts"} onExport={() => exportChart("delai-embauche.csv", "time-to-hire", "rapidité d’embauche")}>
          <div className="histogram"><div className="histogram-median" style={{ left: `${medianPosition}%` }}><span>Médiane : {medianDays ?? "—"} jours</span></div>{histogramBins.map((item: any) => {
            const count = Number(unwrap(item.value ?? item.count)) || 0;
            const heightMax = Math.max(1, ...histogramValues);
            return <div key={item.bin}><b>{count}</b><i style={{ height: `${Math.max(8, count / heightMax * 140)}px` }} /><span>{item.bin}</span></div>;
          })}</div>
        </Card>
        <div className="stat-pair"><Card title="Au moins 1 entretien"><strong>{timing?.interview_share ?? "—"}%</strong></Card><Card title="Réponse employeur"><strong>{quality ? `${quality.employer_response_rate ?? "—"}%` : "…"} </strong></Card></div>
      </div>
    </section>

    <div className="observatory-section-title"><span>3 · OÙ AGIR</span><h2>Où se situent les écarts entre offre d’emploi, candidats et formations ?</h2></div>
    <Card title="Carte des gouvernorats" question="Pression entre candidats, postes et formations" footer={governorates?.meta?.source ?? "Mahara Match · geoBoundaries TUN ADM1"} className="map-card" onExport={() => exportChart("gouvernorats.csv", "governorates", "carte des gouvernorats")}>
      <GovernorateMap data={governorates?.rows} meta={governorates?.meta} onSelect={() => undefined} />
    </Card>
    <Card title="Jeunes 15–24 ans : candidats et embauches par gouvernorat" question="Jeunes candidats et embauches déclarées" footer="Mahara Match · ApplicationStatusEvent" onExport={() => exportChart("jeunes-gouvernorats.csv", "youth-by-governorate", "jeunes par gouvernorat")}>
      <div className="youth-bars">{(youthGovernorates?.rows ?? []).filter((row: any) => row.code !== "unspecified").sort((left: any, right: any) => (Number(unwrap(right.youth_candidates)) || 0) - (Number(unwrap(left.youth_candidates)) || 0)).slice(0, showAllYouth ? 24 : 6).map((row: any) => {
        const candidates = unwrap(row.youth_candidates);
        const hires = unwrap(row.youth_hires);
        return <div className="youth-bar-row" key={row.code}><span>{row.name_fr}</span><i className="candidates" style={{ width: `${Math.min(100, Number(candidates) || 0)}%` }} /><i className="hires" style={{ width: `${Math.min(100, Number(hires) || 0)}%` }} /><b>{hires === "—" ? "<5" : hires}</b></div>;
      })}<button className="button button-secondary youth-expand" type="button" onClick={() => setShowAllYouth((current) => !current)}>{showAllYouth ? "Réduire" : "Voir tout (24)"}</button></div>
    </Card>
    <Card title="Écart de compétences : offre contre candidats" question="Demande publiée face à la disponibilité des candidats" footer={skills?.meta?.source ?? "Mahara Match"} onExport={() => exportChart("ecart-competences.csv", "skills-gap", "écart de compétences")}>
      <div className="butterfly">{(skills?.rows ?? []).map((row: any) => {
        const demand = unwrap(row.demand) ?? 0;
        const supply = unwrap(row.supply) ?? 0;
        const status = row.status === "shortage" ? "▲ Pénurie" : row.status === "surplus" ? "▼ Excédent" : "• Équilibré";
        return <div className="butterfly-row" key={row.skill_id}><b className="demand">{demand}</b><i className="bar-demand" style={{ width: `${Math.min(100, Number(demand) * 4)}%` }} /><span>{row.canonical_name_fr}</span><i className="bar-supply" style={{ width: `${Math.min(100, Number(supply) * 4)}%` }} /><b className="supply">{supply}</b><em>{status}</em></div>;
      })}</div>
    </Card>
    <Card title="Les formations répondent-elles à la demande des employeurs ?" question="Capacité de formation face aux besoins publiés" footer="Mahara Match · La nomenclature sectorielle 2017 est une aide historique à la dénomination seulement." className="training-card" onExport={() => exportChart("alignement-formations.csv", "training-alignment", "alignement des formations")}>
      <div className="table-scroll"><table><thead><tr><th>Compétence demandée</th><th>Offres</th><th>Formations publiées</th><th>Places</th><th>Inscrits</th><th>Achèvement</th><th>Couverture</th></tr></thead><tbody>{(training?.rows ?? []).map((row: any) => <tr key={row.skill_id}><th>{row.canonical_name_fr}</th><td>{unwrap(row.demand) ?? "—"}</td><td>{unwrap(row.published_courses) ?? "—"}</td><td>{unwrap(row.total_seats) ?? "—"}</td><td>{unwrap(row.active_enrollments) ?? "—"}</td><td>{row.completion_rate == null ? "—" : `${Math.round(row.completion_rate * 100)} %`}</td><td><Status>{row.coverage_status}</Status></td></tr>)}</tbody></table></div>
    </Card>
    <Card title="Employeurs et fiabilité des données" question="Réponse des organisations et complétude des données" footer={quality?.meta?.source ?? "Mahara Match"} onExport={() => exportChart("qualite-employeurs.csv", "employers-quality", "qualité employeurs")}>
      {!quality ? <p>{errors["employers-quality"] ?? "Chargement des indicateurs…"}</p> : <div className="quality-grid">
        <div><strong className="big-stat">{unwrap(quality.active_organisations) ?? "—"}</strong><p>Organisations actives</p></div>
        <div className="quality-progress"><label>Candidatures avec une décision de l’employeur<b>{quality.employer_response_rate ?? "—"} %</b></label><i><span style={{ width: `${quality.employer_response_rate ?? 0}%` }} /></i>
          <label>Profils avec gouvernorat renseigné<b>{quality.candidate_profiles_with_governorate_share ?? "—"} %</b></label><i><span style={{ width: `${quality.candidate_profiles_with_governorate_share ?? 0}%` }} /></i>
          <label>Compétences reconnues après normalisation<b>{quality.skills_recognised_share ?? "—"} %</b></label><i><span style={{ width: `${quality.skills_recognised_share ?? 0}%` }} /></i></div>
      </div>}
      {!!quality?.warnings?.length && <div className="quality-warnings" role="alert">{quality.warnings.map((warning: string) => <p key={warning}>⚠ {warning}</p>)}</div>}
    </Card>
  </main>;
}
