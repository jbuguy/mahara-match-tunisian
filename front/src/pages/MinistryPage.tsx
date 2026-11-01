import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { API_BASE_URL, requestJson } from '../lib/api'

type Section = 'skills' | 'occupations' | 'suggestions' | 'datasets' | 'labour-market' | 'analytics' | 'ingestion' | 'monitoring' | 'audit'
type Page<T> = { items: T[]; total: number; page: number; page_size: number }
type Row = Record<string, unknown>
type SkillGapMap = { period_start: string; period_end: string; k_anonymity: number; cells_suppressed: number; cells: Row[] }
type Overview = { module: string; status: string; uptime_seconds: number; database_latency_ms: number | null; requests_total: number; refusals_total: number; errors_total: number }
type LabourMarket = { period_start: string; period_end: string; comparison_period_start: string; comparison_period_end: string; definition_version: string; k_anonymity: number; cells_suppressed: number; demand_by_governorate: Row[]; occupations_under_tension: Row[] }
type UploadPreview = { preview_id: string; expires_at: string; records_total: number; records_valid: number; records_invalid: number; sample: Row[]; rejections: { index: number; reason: string }[] }
type TaxonomyKind = 'skills' | 'occupations'
type Requirement = 'required' | 'preferred'
type RequiredSkill = { skill_code: string; requirement: Requirement }
type SkillRow = { code: string; label_fr: string; label_ar: string | null; label_derja: string | null; alt_labels: string[]; skill_type: string; status: string; version: number }
type OccupationRow = { code: string; isco_code: string | null; title_fr: string; title_ar: string | null; alt_titles: string[]; sector_code: string | null; status: string; skills: RequiredSkill[] }
type Removal = { code: string; outcome: string }
type IngestionJob = { job_id: string; source: string; status: string; pipeline_version: string; records_total: number; records_ok: number; records_failed: number; errors: Row[]; started_at: string | null; finished_at: string | null; created_at: string }
type RouteStats = { route: string; requests: number; refusals: number; errors: number; avg_ms: number; max_ms: number }
type TaxonomyStats = { skills: Record<string, number>; occupations: Record<string, number>; suggestions: Record<string, number>; occupations_without_skills: number }
type MonitoringDetail = { routes: RouteStats[] | null; routesError: string; taxonomy: TaxonomyStats | null; taxonomyError: string }
type JobDetail = { jobId: string; report: IngestionJob | null; loading: boolean; error: string }
type Editor = { kind: TaxonomyKind; mode: 'create' } | { kind: TaxonomyKind; mode: 'edit' | 'skills'; row: Row }

const taxonomyPaths: Record<TaxonomyKind, string> = {
  skills: '/api/v1/admin/taxonomy/skills',
  occupations: '/api/v1/admin/taxonomy/occupations',
}
const statusLabels: Record<string, string> = { draft: 'brouillon', validated: 'validé', deprecated: 'déprécié' }
const requirementLabels: Record<Requirement, string> = { required: 'Obligatoire', preferred: 'Souhaitée' }
const skillTypeLabels: Record<string, string> = { hard: 'Technique / métier', soft: 'Transversale', language: 'Langue' }

function entryLabel(kind: TaxonomyKind, code: string): string {
  return kind === 'skills' ? `La compétence ${code}` : `Le métier ${code}`
}

// French past participles agree with the entry: « validé » for a métier, « validée » for a compétence.
function agreed(kind: TaxonomyKind, participle: string): string {
  return kind === 'skills' ? `${participle}e` : participle
}

function removalNotice(kind: TaxonomyKind, removal: Removal): string {
  const entry = entryLabel(kind, removal.code)
  if (removal.outcome === 'deleted') return `${entry} a été ${agreed(kind, 'supprimé')} définitivement (c’était un brouillon)${kind === 'skills' ? ' et ne figure plus dans aucune fiche métier' : ''}.`
  if (removal.outcome === 'deprecated') return `${entry} a été ${agreed(kind, 'déprécié')} au lieu d’être ${agreed(kind, 'supprimé')} : ${kind === 'skills' ? 'elle reste rattachée aux profils existants' : 'il reste rattaché aux offres existantes'}, mais n’est plus ${agreed(kind, 'proposé')}.`
  return `${entry} : résultat du retrait « ${removal.outcome} ».`
}

function linesOf(value: string): string[] {
  return value.split('\n').map((item) => item.trim()).filter(Boolean)
}

function textOrNull(value: string): string | null {
  return value.trim() || null
}

/** Keep only the fields that differ from the row: PATCH routes apply exactly what they receive. */
function changedFields(next: Record<string, unknown>, original: Row): Record<string, unknown> {
  return Object.fromEntries(Object.entries(next).filter(([key, item]) => JSON.stringify(item) !== JSON.stringify(original[key] ?? null)))
}

function OccupationForm({ occupation, busy, onSubmit, onCancel }: { occupation: OccupationRow | null; busy: boolean; onSubmit: (payload: Record<string, unknown>) => void; onCancel: () => void }) {
  const [code, setCode] = useState('')
  const [titleFr, setTitleFr] = useState(occupation?.title_fr ?? '')
  const [titleAr, setTitleAr] = useState(occupation?.title_ar ?? '')
  const [iscoCode, setIscoCode] = useState(occupation?.isco_code ?? '')
  const [sectorCode, setSectorCode] = useState(occupation?.sector_code ?? '')
  const [altTitles, setAltTitles] = useState((occupation?.alt_titles ?? []).join('\n'))
  const [description, setDescription] = useState('')
  const [formError, setFormError] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    setFormError('')
    const fields = { title_fr: titleFr.trim(), title_ar: textOrNull(titleAr), isco_code: textOrNull(iscoCode), sector_code: textOrNull(sectorCode), alt_titles: linesOf(altTitles) }
    const extra = description.trim() ? { description: description.trim() } : {}
    if (!occupation) return onSubmit({ code: code.trim(), ...fields, ...extra })
    const changes = { ...changedFields(fields, occupation), ...extra }
    if (!Object.keys(changes).length) return setFormError('Aucune modification à enregistrer.')
    onSubmit(changes)
  }

  return <form className="ministry-decision-form" onSubmit={submit}>
    <h5>{occupation ? `Corriger le métier ${occupation.code}` : 'Nouveau métier'}</h5>
    <p className="ministry-cell-subtitle">{occupation ? `Correction éditoriale : le statut (${statusLabels[occupation.status] ?? occupation.status}) ne change pas.` : 'Le métier sera créé en brouillon. Sa validation est une étape séparée.'}</p>
    {!occupation && <label>Code ROME<input required maxLength={32} value={code} onChange={(event) => setCode(event.target.value)} placeholder="ROME-H2913" /></label>}
    <label>Intitulé français<input required maxLength={200} value={titleFr} onChange={(event) => setTitleFr(event.target.value)} /></label>
    <label>Intitulé arabe<input dir="rtl" maxLength={200} value={titleAr} onChange={(event) => setTitleAr(event.target.value)} /></label>
    <label>Code CITP (ISCO-08)<input maxLength={8} value={iscoCode} onChange={(event) => setIscoCode(event.target.value)} placeholder="7212" /></label>
    <label>Code secteur<input maxLength={32} value={sectorCode} onChange={(event) => setSectorCode(event.target.value)} placeholder="Facultatif — doit exister dans le référentiel des secteurs" /></label>
    <label>Intitulés alternatifs (un par ligne)<textarea value={altTitles} onChange={(event) => setAltTitles(event.target.value)} /></label>
    <label>Description{occupation && ' — laissez vide pour conserver la description actuelle'}<textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label>
    {formError && <p className="form-error" role="alert">{formError}</p>}
    <div className="ministry-form-actions">
      <button className="primary-btn" type="submit" disabled={busy}>{busy ? 'Enregistrement…' : occupation ? 'Enregistrer la correction' : 'Créer en brouillon'}</button>
      <button className="secondary-btn" type="button" onClick={onCancel} disabled={busy}>Annuler</button>
    </div>
  </form>
}

function SkillForm({ skill, busy, onSubmit, onCancel }: { skill: SkillRow | null; busy: boolean; onSubmit: (payload: Record<string, unknown>) => void; onCancel: () => void }) {
  const [code, setCode] = useState('')
  const [labelFr, setLabelFr] = useState(skill?.label_fr ?? '')
  const [labelAr, setLabelAr] = useState(skill?.label_ar ?? '')
  const [labelDerja, setLabelDerja] = useState(skill?.label_derja ?? '')
  const [altLabels, setAltLabels] = useState((skill?.alt_labels ?? []).join('\n'))
  const [skillType, setSkillType] = useState(skill?.skill_type ?? 'hard')
  const [description, setDescription] = useState('')
  const [formError, setFormError] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    setFormError('')
    const fields = { label_fr: labelFr.trim(), label_ar: textOrNull(labelAr), label_derja: textOrNull(labelDerja), alt_labels: linesOf(altLabels), skill_type: skillType }
    const extra = description.trim() ? { description: description.trim() } : {}
    if (!skill) return onSubmit({ code: code.trim(), ...fields, ...extra })
    const changes = { ...changedFields(fields, skill), ...extra }
    if (!Object.keys(changes).length) return setFormError('Aucune modification à enregistrer.')
    onSubmit(changes)
  }

  return <form className="ministry-decision-form" onSubmit={submit}>
    <h5>{skill ? `Corriger la compétence ${skill.code}` : 'Nouvelle compétence'}</h5>
    <p className="ministry-cell-subtitle">{skill ? `Correction éditoriale : la version passera de ${skill.version} à ${skill.version + 1} ; le statut (${statusLabels[skill.status] ?? skill.status}) ne change pas.` : 'La compétence sera créée en brouillon. Sa validation est une étape séparée.'}</p>
    {!skill && <label>Code REM<input required maxLength={32} value={code} onChange={(event) => setCode(event.target.value)} placeholder="REM-E1204" /></label>}
    <label>Libellé français<input required maxLength={200} value={labelFr} onChange={(event) => setLabelFr(event.target.value)} /></label>
    <label>Libellé arabe<input dir="rtl" maxLength={200} value={labelAr} onChange={(event) => setLabelAr(event.target.value)} /></label>
    <label>Libellé en derja<input maxLength={200} value={labelDerja} onChange={(event) => setLabelDerja(event.target.value)} /></label>
    <label>Catégorie<select value={skillType} onChange={(event) => setSkillType(event.target.value)}>{Object.entries(skillTypeLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
    <label>Synonymes (un par ligne, toute langue)<textarea value={altLabels} onChange={(event) => setAltLabels(event.target.value)} /></label>
    <label>Description{skill && ' — laissez vide pour conserver la description actuelle'}<textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label>
    {formError && <p className="form-error" role="alert">{formError}</p>}
    <div className="ministry-form-actions">
      <button className="primary-btn" type="submit" disabled={busy}>{busy ? 'Enregistrement…' : skill ? 'Enregistrer la correction' : 'Créer en brouillon'}</button>
      <button className="secondary-btn" type="button" onClick={onCancel} disabled={busy}>Annuler</button>
    </div>
  </form>
}

const suggestionStatusLabels: Record<string, string> = { pending: 'En attente', approved: 'Homologuées', merged: 'Fusionnées', rejected: 'Rejetées' }
const ROUTES_PREVIEW = 20

function RouteTraffic({ routes, error }: { routes: RouteStats[] | null; error: string }) {
  const [showAll, setShowAll] = useState(false)
  if (error) return <div className="ministry-alert error" role="alert"><strong>Trafic indisponible</strong><span>{error}</span></div>
  if (!routes) return null
  if (!routes.length) return <div className="ministry-empty-selection"><strong>Aucun appel enregistré</strong><p>Les compteurs repartent de zéro à chaque redémarrage du service.</p></div>
  const visible = showAll ? routes : routes.slice(0, ROUTES_PREVIEW)
  return <>
    <div className="ministry-table-wrap"><table className="ministry-table"><thead><tr><th scope="col">Route</th><th scope="col">Appels</th><th scope="col">Refus (4xx)</th><th scope="col">Erreurs (5xx)</th><th scope="col">Durée moyenne</th><th scope="col">Durée maximale</th></tr></thead>
      <tbody>{visible.map((row) => <tr key={row.route}><td>{row.route}</td><td>{row.requests}</td><td>{row.refusals}</td><td>{row.errors}</td><td>{row.avg_ms} ms</td><td>{row.max_ms} ms</td></tr>)}</tbody></table></div>
    {routes.length > ROUTES_PREVIEW && <button className="ghost-btn" type="button" onClick={() => setShowAll(!showAll)}>{showAll ? `Afficher les ${ROUTES_PREVIEW} routes les plus sollicitées` : `Afficher toutes les routes (${routes.length})`}</button>}
    <p className="ministry-cell-subtitle">Les chemins contenant un code (métier, compétence, lot) apparaissent un par un : le compteur de la plateforme enregistre l’URL appelée.</p>
  </>
}

function TaxonomyQuality({ stats, error }: { stats: TaxonomyStats | null; error: string }) {
  if (error) return <div className="ministry-alert error" role="alert"><strong>Indicateurs du référentiel indisponibles</strong><span>{error}</span></div>
  if (!stats) return null
  const statuses = Object.keys(statusLabels)
  const suggestionEntries = Object.entries(stats.suggestions)
  return <>
    <div className="ministry-metrics-row">
      <div><span>Propositions en attente</span><strong>{stats.suggestions.pending ?? 0}</strong></div>
      <div><span>Métiers sans compétence requise (tous statuts)</span><strong>{stats.occupations_without_skills}</strong></div>
      <div><span>Compétences en brouillon</span><strong>{stats.skills.draft ?? 0}</strong></div>
    </div>
    <div className="ministry-market-grid">
      <section><h4>Référentiel par statut</h4><div className="ministry-table-wrap"><table className="ministry-table"><thead><tr><th scope="col">Statut</th><th scope="col">Compétences</th><th scope="col">Métiers</th></tr></thead>
        <tbody>{statuses.map((status) => <tr key={status}><td>{statusLabels[status]}</td><td>{stats.skills[status] ?? 0}</td><td>{stats.occupations[status] ?? 0}</td></tr>)}</tbody></table></div></section>
      <section><h4>Propositions par décision</h4>{suggestionEntries.length ? <div className="ministry-table-wrap"><table className="ministry-table"><thead><tr><th scope="col">Décision</th><th scope="col">Nombre</th></tr></thead>
        <tbody>{suggestionEntries.map(([status, count]) => <tr key={status}><td>{suggestionStatusLabels[status] ?? status}</td><td>{count}</td></tr>)}</tbody></table></div> : <p>Aucune proposition reçue des pipelines.</p>}</section>
    </div>
  </>
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString('fr-FR') : '—'
}

function JobReport({ detail, onRetry, onClose }: { detail: JobDetail; onRetry: () => void; onClose: () => void }) {
  const { report } = detail
  // Market ingestion writes {index, reason}; other stages (e.g. the worker's fetch) write other shapes.
  const rejections = report?.errors.filter((item) => typeof item.index === 'number' && typeof item.reason === 'string') ?? []
  const otherErrors = report?.errors.filter((item) => !rejections.includes(item)) ?? []

  return <div className="ministry-decision-form">
    <h5>Rapport du lot {detail.jobId}</h5>
    {detail.loading && <div className="ministry-loading" role="status"><span className="loading-line" /><span className="loading-line short" />Chargement du rapport…</div>}
    {!detail.loading && detail.error && <div className="ministry-alert error" role="alert"><strong>Rapport indisponible</strong><span>{detail.error}</span><button className="secondary-btn" type="button" onClick={onRetry}>Réessayer</button></div>}
    {!detail.loading && report && <>
      <dl>
        <div><dt>Source</dt><dd>{report.source}</dd></div>
        <div><dt>Statut</dt><dd>{report.status}</dd></div>
        <div><dt>Enregistrements reçus</dt><dd>{report.records_total}</dd></div>
        <div><dt>Acceptés / rejetés</dt><dd>{report.records_ok} / {report.records_failed}</dd></div>
        <div><dt>Version du pipeline</dt><dd>{report.pipeline_version}</dd></div>
        <div><dt>Créé · démarré · terminé</dt><dd>{formatDate(report.created_at)} · {formatDate(report.started_at)} · {formatDate(report.finished_at)}</dd></div>
      </dl>
      <h5>Lignes rejetées ({rejections.length})</h5>
      {rejections.length ? <div className="ministry-table-wrap"><table className="ministry-table"><thead><tr><th scope="col">Index</th><th scope="col">Rang dans le lot</th><th scope="col">Motif du rejet</th></tr></thead><tbody>{rejections.map((item) => <tr key={String(item.index)}><td>{String(item.index)}</td><td>{Number(item.index) + 1}</td><td>{String(item.reason)}</td></tr>)}</tbody></table></div>
        : <div className="ministry-empty-selection"><strong>Aucune ligne rejetée</strong><p>Tous les enregistrements reçus ont été conservés.</p></div>}
      <p className="ministry-cell-subtitle">L’index désigne la position de l’enregistrement dans le lot soumis au pipeline (à partir de 0), pas une ligne du fichier d’origine.</p>
      {otherErrors.length > 0 && <><h5>Autres erreurs du traitement</h5><ul>{otherErrors.map((item, index) => <li key={index}>{typeof item.stage === 'string' ? `${item.stage} : ` : ''}{typeof item.reason === 'string' ? item.reason : JSON.stringify(item)}</li>)}</ul></>}
    </>}
    <div className="ministry-form-actions"><button className="secondary-btn" type="button" onClick={onClose}>Fermer le rapport</button></div>
  </div>
}

function RequiredSkillsEditor({ occupation, busy, onSave, onCancel }: { occupation: OccupationRow; busy: boolean; onSave: (skills: RequiredSkill[], summary: string) => void; onCancel: () => void }) {
  const [lines, setLines] = useState<RequiredSkill[]>(occupation.skills)
  const [newCode, setNewCode] = useState('')
  const [newRequirement, setNewRequirement] = useState<Requirement>('required')
  const [formError, setFormError] = useState('')
  const original = new Map(occupation.skills.map((line) => [line.skill_code, line.requirement]))
  const current = new Set(lines.map((line) => line.skill_code))
  const added = lines.filter((line) => !original.has(line.skill_code))
  const removed = occupation.skills.filter((line) => !current.has(line.skill_code))
  const changed = lines.filter((line) => original.has(line.skill_code) && original.get(line.skill_code) !== line.requirement)
  const dirty = added.length + removed.length + changed.length > 0
  const summary = `${added.length} ajout(s), ${removed.length} retrait(s), ${changed.length} exigence(s) modifiée(s)`

  function addLine(event: FormEvent) {
    event.preventDefault()
    const skillCode = newCode.trim()
    if (!skillCode) return
    if (current.has(skillCode)) return setFormError(`${skillCode} figure déjà dans la liste.`)
    setLines([...lines, { skill_code: skillCode, requirement: newRequirement }])
    setNewCode('')
    setFormError('')
  }

  return <div className="ministry-decision-form">
    <h5>Compétences requises — {occupation.title_fr} ({occupation.code})</h5>
    <div className="ministry-privacy-note"><strong>L’enregistrement remplace la liste entière</strong><span>La fiche aura exactement les compétences listées ci-dessous. Pour en retirer une, retirez-la de la liste puis enregistrez.</span></div>
    {lines.length ? <div className="ministry-table-wrap"><table className="ministry-table"><thead><tr><th scope="col">Compétence</th><th scope="col">Exigence</th><th scope="col">Action</th></tr></thead><tbody>{lines.map((line) => <tr key={line.skill_code}>
      <td>{line.skill_code}{!original.has(line.skill_code) && <small className="ministry-cell-subtitle">Ajoutée — pas encore enregistrée</small>}</td>
      <td><select aria-label={`Exigence pour ${line.skill_code}`} value={line.requirement} onChange={(event) => setLines(lines.map((item) => item.skill_code === line.skill_code ? { ...item, requirement: event.target.value as Requirement } : item))}>{Object.entries(requirementLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></td>
      <td><button className="danger-text-btn" type="button" onClick={() => setLines(lines.filter((item) => item.skill_code !== line.skill_code))}>Retirer de la liste</button></td>
    </tr>)}</tbody></table></div> : <div className="ministry-empty-selection"><strong>Aucune compétence requise</strong><p>{occupation.skills.length ? 'Enregistrer maintenant videra la liste de ce métier.' : 'Ajoutez les compétences attendues pour ce métier.'}</p></div>}
    {removed.length > 0 && <p className="form-error">Seront retirées à l’enregistrement : {removed.map((line) => line.skill_code).join(', ')}</p>}
    <form className="ministry-inline-form" onSubmit={addLine}>
      <label>Ajouter une compétence (code)<input value={newCode} maxLength={32} onChange={(event) => setNewCode(event.target.value)} placeholder="REM-E1204" /></label>
      <label>Exigence<select value={newRequirement} onChange={(event) => setNewRequirement(event.target.value as Requirement)}>{Object.entries(requirementLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <button className="secondary-btn" type="submit" disabled={!newCode.trim()}>Ajouter à la liste</button>
    </form>
    {formError && <p className="form-error" role="alert">{formError}</p>}
    <p className="ministry-cell-subtitle">{dirty ? `Modifications non enregistrées : ${summary}.` : 'Aucune modification par rapport à la fiche enregistrée.'}</p>
    <div className="ministry-form-actions">
      <button className="primary-btn" type="button" disabled={busy || !dirty} onClick={() => onSave(lines, summary)}>{busy ? 'Enregistrement…' : lines.length ? `Remplacer la liste (${lines.length} compétence${lines.length === 1 ? '' : 's'})` : 'Vider la liste des compétences requises'}</button>
      <button className="secondary-btn" type="button" onClick={onCancel} disabled={busy}>Annuler</button>
    </div>
  </div>
}

const sections: { id: Section; label: string; endpoint: string }[] = [
  { id: 'skills', label: 'Compétences (REM)', endpoint: '/api/v1/admin/taxonomy/skills?page=1&page_size=50' },
  { id: 'occupations', label: 'Métiers & fiches (ROME)', endpoint: '/api/v1/admin/taxonomy/occupations?page=1&page_size=50' },
  { id: 'suggestions', label: 'Propositions & arbitrage', endpoint: '/api/v1/admin/taxonomy/suggestions?page=1&page_size=50' },
  { id: 'datasets', label: 'Observatoire du marché', endpoint: '/api/v1/admin/market/datasets?page=1&page_size=50' },
  { id: 'labour-market', label: 'Tensions territoriales', endpoint: '/api/v1/admin/analytics/labour-market' },
  { id: 'analytics', label: 'Analytique & rapports', endpoint: '/api/v1/admin/analytics/skill-gaps' },
  { id: 'ingestion', label: 'Ingestion de lots', endpoint: '/api/v1/admin/ingestion/jobs?page=1&page_size=50' },
  { id: 'monitoring', label: 'Santé des services', endpoint: '/api/v1/admin/monitoring/overview' },
  { id: 'audit', label: 'Journal d’audit', endpoint: '/api/v1/admin/monitoring/audit?page=1&page_size=50' },
]

function value(row: Row, key: string): string {
  const item = row[key]
  if (item === null || item === undefined || item === '') return '—'
  if (typeof item === 'object') return JSON.stringify(item)
  return String(item)
}

// value() renders a missing field as '—', which is truthy: read the raw identifiers instead.
function rowKey(row: Row, index: number): string {
  const id = ['skill_id', 'occupation_id', 'dataset_id', 'job_id', 'id'].map((key) => row[key]).find((item) => typeof item === 'string' || typeof item === 'number')
  return id === undefined ? String(index) : String(id)
}

function tableData(data: unknown): Row[] | null {
  if (data && typeof data === 'object' && 'items' in data && Array.isArray(data.items)) return data.items as Row[]
  if (data && typeof data === 'object' && 'cells' in data && Array.isArray(data.cells)) return data.cells as Row[]
  return null
}

export function MinistryPage() {
  const [section, setSection] = useState<Section>('suggestions')
  const [data, setData] = useState<unknown>(null)
  const [analytics, setAnalytics] = useState<SkillGapMap | null>(null)
  const [overview, setOverview] = useState<Overview | null>(null)
  const [labourMarket, setLabourMarket] = useState<LabourMarket | null>(null)
  const [pendingSuggestionCount, setPendingSuggestionCount] = useState<number | null>(null)
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<Row | null>(null)
  const [skillCode, setSkillCode] = useState('')
  const [skillLabel, setSkillLabel] = useState('')
  const [skillType, setSkillType] = useState('hard')
  const [mergeCode, setMergeCode] = useState('')
  const [rejectReason, setRejectReason] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [page, setPage] = useState(1)
  const [marketFile, setMarketFile] = useState<File | null>(null)
  const [marketTitle, setMarketTitle] = useState('')
  const [marketPublisher, setMarketPublisher] = useState('')
  const [marketPeriodStart, setMarketPeriodStart] = useState('')
  const [marketPeriodEnd, setMarketPeriodEnd] = useState('')
  const [uploadPreview, setUploadPreview] = useState<UploadPreview | null>(null)
  const [acceptValidRows, setAcceptValidRows] = useState(false)
  const [editor, setEditor] = useState<Editor | null>(null)
  // Separate from `error`, which means the list failed to load and hides it.
  const [actionError, setActionError] = useState('')
  const [jobDetail, setJobDetail] = useState<JobDetail | null>(null)
  const [monitoring, setMonitoring] = useState<MonitoringDetail>({ routes: null, routesError: '', taxonomy: null, taxonomyError: '' })

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const endpoint = sections.find((item) => item.id === section)!.endpoint.replace('page=1', `page=${page}`)
      const result = await requestJson<unknown>(endpoint)
      setData(result)
      if (section === 'analytics') setAnalytics(result as SkillGapMap)
      if (section === 'monitoring') {
        setOverview(result as Overview)
        // Each panel fails on its own: one unavailable indicator must not hide the other.
        const [routes, taxonomy] = await Promise.allSettled([
          requestJson<RouteStats[]>('/api/v1/admin/monitoring/routes'),
          requestJson<TaxonomyStats>('/api/v1/admin/monitoring/taxonomy'),
        ])
        const reason = (outcome: PromiseRejectedResult) => outcome.reason instanceof Error ? outcome.reason.message : 'Indicateur indisponible.'
        setMonitoring({
          routes: routes.status === 'fulfilled' ? routes.value : null,
          routesError: routes.status === 'rejected' ? reason(routes) : '',
          taxonomy: taxonomy.status === 'fulfilled' ? taxonomy.value : null,
          taxonomyError: taxonomy.status === 'rejected' ? reason(taxonomy) : '',
        })
      }
      if (section === 'labour-market') setLabourMarket(result as LabourMarket)
    } catch (cause) {
      setData(null)
      setError(cause instanceof Error ? cause.message : 'Impossible de charger les données ministérielles.')
    } finally {
      setLoading(false)
    }
  }, [section, page])

  useEffect(() => { void load(); setSelected(null); setQuery(''); setEditor(null); setActionError(''); setJobDetail(null) }, [load])
  useEffect(() => {
    if (!localStorage.getItem('mahara_access_token')) return
    void Promise.allSettled([
      requestJson<SkillGapMap>(sections.find((item) => item.id === 'analytics')!.endpoint),
      requestJson<Overview>(sections.find((item) => item.id === 'monitoring')!.endpoint),
      requestJson<Page<Row>>(sections.find((item) => item.id === 'suggestions')!.endpoint),
      requestJson<LabourMarket>(sections.find((item) => item.id === 'labour-market')!.endpoint),
    ]).then(([gaps, status, suggestions, market]) => {
      if (gaps.status === 'fulfilled') setAnalytics(gaps.value)
      if (status.status === 'fulfilled') setOverview(status.value)
      if (suggestions.status === 'fulfilled') setPendingSuggestionCount(suggestions.value.total)
      if (market.status === 'fulfilled') setLabourMarket(market.value)
    })
  }, [])

  const rows = tableData(data)
  const filteredRows = useMemo(() => rows?.filter((row) => JSON.stringify(row).toLocaleLowerCase().includes(query.toLocaleLowerCase())) ?? [], [rows, query])
  const activeSection = sections.find((item) => item.id === section)!
  const total = data && typeof data === 'object' && 'total' in data && typeof data.total === 'number' ? data.total : rows?.length ?? 0
  const taxonomyKind: TaxonomyKind | null = section === 'skills' || section === 'occupations' ? section : null

  /** Run one governance act, then show what the API actually reported and refresh the list. */
  async function runAction(perform: () => Promise<string>) {
    setBusy(true); setActionError(''); setNotice('')
    try {
      setNotice(await perform())
      setEditor(null)
      await load()
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : 'L’opération n’a pas pu aboutir.')
    } finally { setBusy(false) }
  }

  function entryPath(kind: TaxonomyKind, code: string): string {
    return `${taxonomyPaths[kind]}/${encodeURIComponent(code)}`
  }

  function validateEntry(kind: TaxonomyKind, code: string) {
    void runAction(async () => {
      await requestJson(`${entryPath(kind, code)}/validate`, { method: 'POST' })
      return `${entryLabel(kind, code)} a été ${agreed(kind, 'validé')}.`
    })
  }

  function removeEntry(kind: TaxonomyKind, code: string) {
    // Mirrors the backend: a draft skill required by occupations is still deleted, and the
    // occupation_skills foreign key cascades, so those requirement lines go with it.
    const draftRule = kind === 'skills'
      ? 'Un brouillon est supprimé définitivement, et retiré des fiches métiers qui l’exigent'
      : 'Un brouillon est supprimé définitivement, avec sa liste de compétences requises'
    if (!window.confirm(`Retirer ${code} ? ${draftRule} ; une entrée déjà utilisée ailleurs ou validée est dépréciée et conservée pour l’historique.`)) return
    void runAction(async () => removalNotice(kind, await requestJson<Removal>(entryPath(kind, code), { method: 'DELETE' })))
  }

  function createOccupation(payload: Record<string, unknown>) {
    void runAction(async () => {
      const created = await requestJson<OccupationRow>(taxonomyPaths.occupations, { method: 'POST', body: JSON.stringify(payload) })
      return `Le métier ${created.code} a été créé (statut : ${statusLabels[created.status] ?? created.status}). Sa validation est une étape séparée.`
    })
  }

  function updateOccupation(code: string, changes: Record<string, unknown>) {
    void runAction(async () => {
      const updated = await requestJson<OccupationRow>(entryPath('occupations', code), { method: 'PATCH', body: JSON.stringify(changes) })
      return `Le métier ${updated.code} a été corrigé (${Object.keys(changes).join(', ')}). Statut inchangé : ${statusLabels[updated.status] ?? updated.status}.`
    })
  }

  function createSkill(payload: Record<string, unknown>) {
    void runAction(async () => {
      const created = await requestJson<SkillRow>(taxonomyPaths.skills, { method: 'POST', body: JSON.stringify(payload) })
      return `La compétence ${created.code} a été créée (statut : ${statusLabels[created.status] ?? created.status}). Sa validation est une étape séparée.`
    })
  }

  function updateSkill(code: string, changes: Record<string, unknown>) {
    void runAction(async () => {
      const updated = await requestJson<SkillRow>(entryPath('skills', code), { method: 'PATCH', body: JSON.stringify(changes) })
      return `La compétence ${updated.code} a été corrigée (${Object.keys(changes).join(', ')}) : version ${updated.version}, statut inchangé (${statusLabels[updated.status] ?? updated.status}).`
    })
  }

  function saveRequiredSkills(code: string, skills: RequiredSkill[], summary: string) {
    void runAction(async () => {
      const updated = await requestJson<OccupationRow>(`${entryPath('occupations', code)}/skills`, { method: 'PUT', body: JSON.stringify({ skills }) })
      return `Liste des compétences requises du métier ${updated.code} remplacée : ${updated.skills.length} compétence(s) enregistrée(s) (${summary}).`
    })
  }

  function taxonomyActions(kind: TaxonomyKind, row: Row) {
    if (typeof row.code !== 'string') return '—'
    const code = row.code
    return <div className="ministry-row-actions">
      {row.status === 'draft' && <button className="secondary-btn" type="button" disabled={busy} onClick={() => validateEntry(kind, code)}>Valider</button>}
      <button className="ghost-btn" type="button" disabled={busy} onClick={() => setEditor({ kind, mode: 'edit', row })}>Corriger</button>
      {kind === 'occupations' && <button className="ghost-btn" type="button" disabled={busy} onClick={() => setEditor({ kind, mode: 'skills', row })}>Compétences</button>}
      {row.status !== 'deprecated' && <button className="danger-text-btn" type="button" disabled={busy} onClick={() => removeEntry(kind, code)}>Retirer</button>}
    </div>
  }

  async function openJob(jobId: string) {
    setJobDetail({ jobId, report: null, loading: true, error: '' })
    try {
      const report = await requestJson<IngestionJob>(`/api/v1/admin/ingestion/jobs/${encodeURIComponent(jobId)}`)
      setJobDetail({ jobId, report, loading: false, error: '' })
    } catch (cause) {
      setJobDetail({ jobId, report: null, loading: false, error: cause instanceof Error ? cause.message : 'Impossible de charger le rapport du lot.' })
    }
  }

  function jobAction(row: Row) {
    if (typeof row.job_id !== 'string') return '—'
    const jobId = row.job_id
    const failed = typeof row.records_failed === 'number' ? row.records_failed : 0
    return <button className="ghost-btn" type="button" aria-pressed={jobDetail?.jobId === jobId} onClick={() => void openJob(jobId)}>{failed ? `Voir les ${failed} rejet${failed === 1 ? '' : 's'}` : 'Voir le rapport'}</button>
  }

  function renderEditor(current: Editor) {
    const close = () => setEditor(null)
    if (current.kind === 'skills' && current.mode === 'create') return <SkillForm skill={null} busy={busy} onSubmit={createSkill} onCancel={close} />
    if (current.kind === 'skills' && current.mode === 'edit') {
      const skill = current.row as SkillRow
      return <SkillForm key={skill.code} skill={skill} busy={busy} onSubmit={(changes) => updateSkill(skill.code, changes)} onCancel={close} />
    }
    if (current.kind === 'occupations' && current.mode === 'create') return <OccupationForm occupation={null} busy={busy} onSubmit={createOccupation} onCancel={close} />
    if (current.kind === 'occupations' && current.mode === 'edit') {
      const occupation = current.row as OccupationRow
      return <OccupationForm key={occupation.code} occupation={occupation} busy={busy} onSubmit={(changes) => updateOccupation(occupation.code, changes)} onCancel={close} />
    }
    if (current.kind === 'occupations' && current.mode === 'skills') {
      const occupation = current.row as OccupationRow
      return <RequiredSkillsEditor key={occupation.code} occupation={occupation} busy={busy} onSave={(skills, summary) => saveRequiredSkills(occupation.code, skills, summary)} onCancel={close} />
    }
    return null
  }

  async function reviewSuggestion(action: 'approve' | 'merge' | 'reject', event?: FormEvent) {
    event?.preventDefault()
    if (!selected || typeof selected.suggestion_id !== 'string') return
    setBusy(true); setError(''); setNotice('')
    try {
      const base = `/api/v1/admin/taxonomy/suggestions/${encodeURIComponent(selected.suggestion_id)}`
      if (action === 'reject') {
        await requestJson(`${base}/reject`, { method: 'POST', body: JSON.stringify({ reason: rejectReason.trim() }) })
        setNotice('La proposition a été rejetée et inscrite au journal d’audit.')
      } else if (action === 'merge') {
        await requestJson(`${base}/merge`, { method: 'POST', body: JSON.stringify({ code: mergeCode.trim() }) })
        setNotice('La proposition a été fusionnée avec la compétence existante.')
      } else {
        await requestJson(`${base}/approve`, { method: 'POST', body: JSON.stringify({ code: skillCode.trim(), label_fr: skillLabel.trim(), skill_type: skillType }) })
        setNotice('La compétence a été créée en brouillon. Validez-la depuis le référentiel après vérification.')
      }
      setSelected(null)
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'La décision n’a pas pu être enregistrée.')
    } finally { setBusy(false) }
  }

  async function downloadLabourMarketCsv() {
    setExporting(true)
    setError('')
    try {
      const token = localStorage.getItem('mahara_access_token')
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/analytics/labour-market/export.csv`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(typeof body?.detail === 'string' ? body.detail : `Request failed with status ${response.status}`)
      }
      const url = URL.createObjectURL(await response.blob())
      const link = document.createElement('a')
      link.href = url
      link.download = 'mahara-labour-market.csv'
      link.click()
      URL.revokeObjectURL(url)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not export the report.')
    } finally { setExporting(false) }
  }

  async function downloadLabourMarketPdf() {
    setExporting(true); setError('')
    try {
      const token = localStorage.getItem('mahara_access_token')
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/analytics/labour-market/export.pdf`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      if (!response.ok) throw new Error(`Request failed with status ${response.status}`)
      const url = URL.createObjectURL(await response.blob())
      const link = document.createElement('a'); link.href = url; link.download = 'mahara-labour-market.pdf'; link.click(); URL.revokeObjectURL(url)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not export the PDF report.') }
    finally { setExporting(false) }
  }

  async function previewMarketUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!marketFile) return
    setBusy(true); setError(''); setNotice(''); setUploadPreview(null)
    try {
      const form = new FormData()
      form.set('dataset', JSON.stringify({ title: marketTitle, origin: 'official', publisher: marketPublisher, period_start: marketPeriodStart, period_end: marketPeriodEnd }))
      form.set('file', marketFile)
      setUploadPreview(await requestJson<UploadPreview>('/api/v1/admin/market/datasets/upload/preview', { method: 'POST', body: form }))
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not preview the dataset file.') }
    finally { setBusy(false) }
  }

  async function confirmMarketUpload() {
    if (!uploadPreview) return
    setBusy(true); setError(''); setNotice('')
    try {
      const report = await requestJson<{ records_ok: number; records_failed: number }>(`/api/v1/admin/market/datasets/upload/${uploadPreview.preview_id}/confirm`, {
        method: 'POST', body: JSON.stringify({ accept_valid_rows: acceptValidRows }),
      })
      setNotice(`Dataset imported: ${report.records_ok} accepted, ${report.records_failed} rejected.`)
      setUploadPreview(null); setMarketFile(null); await load()
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not import the reviewed dataset.') }
    finally { setBusy(false) }
  }

  async function queueMarketRefresh() {
    setBusy(true); setError(''); setNotice('')
    try {
      const job = await requestJson<{ job_id: string; status: string }>('/api/v1/admin/market/refresh', {
        method: 'POST',
        headers: { 'Idempotency-Key': crypto.randomUUID() },
        body: JSON.stringify({}),
      })
      setNotice(`Actualisation acceptée. Suivi du traitement : ${job.job_id} (${job.status}).`)
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Impossible de lancer l’actualisation officielle.')
    } finally { setBusy(false) }
  }

  if (!localStorage.getItem('mahara_access_token')) {
    return <section className="stacked-view"><h2>Espace ministériel</h2><p>Connectez-vous avec un compte ministériel habilité pour accéder aux référentiels.</p><Link className="primary-btn" to="/signin">Se connecter</Link></section>
  }

  return <main className="stacked-view ministry-console">
    <header className="ministry-hero">
      <div className="ministry-brand-mark" aria-hidden="true">✦</div>
      <div className="ministry-hero-copy">
        <p className="eyebrow">MFPE · ANETI · ROME-TN</p>
        <h2>Espace Ministériel de Régulation</h2>
        <p>Validation des compétences émergentes, conciliation sectorielle REM-Tunisie et coordination de l’Observatoire National.</p>
      </div>
      <div className="ministry-session"><span className={`status-dot ${overview?.status === 'ok' ? 'is-ok' : ''}`} />{overview ? `Services ${overview.status === 'ok' ? 'opérationnels' : 'dégradés'}` : 'Statut des services'}<small>{overview?.module ?? 'Connexion sécurisée'}</small></div>
    </header>

    <div className="ministry-summary-grid">
      <article className="ministry-summary-card"><span>Compétences à arbitrer</span><strong>{pendingSuggestionCount ?? '—'}</strong><small>File des propositions en attente</small></article>
      <article className="ministry-summary-card"><span>Métiers sous tension</span><strong>{labourMarket?.occupations_under_tension.length ?? '—'}</strong><small>{labourMarket ? `${labourMarket.period_start} – ${labourMarket.period_end}` : 'Données agrégées uniquement'}</small></article>
      <article className="ministry-summary-card"><span>État de la plateforme</span><strong>{overview?.status ?? '—'}</strong><small>{overview?.database_latency_ms == null ? 'Latence base indisponible' : `Base de données ${Math.round(overview.database_latency_ms)} ms`}</small></article>
      <article className="ministry-summary-card"><span>Erreurs de service</span><strong>{overview?.errors_total ?? '—'}</strong><small>Compteurs depuis le démarrage du processus</small></article>
    </div>

    <nav className="ministry-nav" aria-label="Sections de régulation">
      {sections.map((item, index) => <button key={item.id} type="button" className={section === item.id ? 'ministry-nav-item active' : 'ministry-nav-item'} aria-current={section === item.id ? 'page' : undefined} onClick={() => { setSection(item.id); setPage(1) }}><span>{String(index + 1).padStart(2, '0')}</span>{item.label}</button>)}
    </nav>

    <section className="ministry-main-card" aria-live="polite">
      <div className="ministry-section-heading">
        <div><p className="eyebrow">Espace de travail · {activeSection.label}</p><h3>{section === 'suggestions' ? 'File d’arbitrage des compétences REM' : activeSection.label}</h3><p>{section === 'suggestions' ? 'Examinez les propositions transmises par les centres de formation et les secteurs professionnels. Chaque décision est conservée dans le journal d’audit.' : 'Consultez les données autorisées par votre habilitation. Les vues analytiques restent agrégées et anonymisées.'}</p></div>
        <div className="ministry-heading-actions">{taxonomyKind && <button className="primary-btn" type="button" onClick={() => setEditor({ kind: taxonomyKind, mode: 'create' })} disabled={busy}>{taxonomyKind === 'skills' ? '＋ Nouvelle compétence' : '＋ Nouveau métier'}</button>}<span className="ministry-record-count">{loading ? 'Chargement…' : `${total} enregistrement${total === 1 ? '' : 's'}`}</span><button className="ghost-btn" type="button" onClick={() => void load()} disabled={loading || busy}>↻ Actualiser</button></div>
      </div>

      {error && <div className="ministry-alert error" role="alert"><strong>{error.includes('403') || error.includes('401') ? 'Accès réservé' : 'La requête a échoué'}</strong><span>{error.includes('403') || error.includes('401') ? 'Votre compte ne dispose pas des privilèges requis pour cette section.' : error}</span><button className="secondary-btn" type="button" onClick={() => void load()} disabled={loading}>Réessayer</button></div>}
      {notice && <p className="form-notice" role="status">{notice}</p>}
      {actionError && <div className="ministry-alert error" role="alert"><strong>L’action n’a pas abouti</strong><span>{actionError}</span><button className="secondary-btn" type="button" onClick={() => setActionError('')}>Fermer</button></div>}
      {editor && editor.kind === taxonomyKind && <section className="ministry-review-detail ministry-editor-panel" aria-label="Édition du référentiel">{renderEditor(editor)}</section>}
      {section === 'ingestion' && jobDetail && <section className="ministry-review-detail ministry-editor-panel" aria-label="Rapport du lot d’ingestion"><JobReport detail={jobDetail} onRetry={() => void openJob(jobDetail.jobId)} onClose={() => setJobDetail(null)} /></section>}

      {section === 'analytics' && analytics && <div className="ministry-privacy-note"><strong>Données agrégées et anonymisées</strong><span>{analytics.cells_suppressed} cellule(s) supprimée(s) sous le seuil de confidentialité k={analytics.k_anonymity}. Aucun dossier candidat individuel n’est affiché.</span></div>}
      {section === 'labour-market' && labourMarket && <div className="ministry-privacy-note"><strong>Données agrégées et anonymisées</strong><span>{labourMarket.cells_suppressed} cellule(s) supprimée(s), seuil k={labourMarket.k_anonymity}. Ratio version {labourMarket.definition_version}. Période de comparaison : {labourMarket.comparison_period_start} – {labourMarket.comparison_period_end}.</span></div>}
      {section === 'labour-market' && labourMarket && <div className="ministry-market-grid"><section><h4>Demande par gouvernorat</h4><div className="ministry-table-wrap"><table className="ministry-table"><thead><tr><th>Gouvernorat</th><th>Postes</th><th>Offres</th></tr></thead><tbody>{labourMarket.demand_by_governorate.map((row) => <tr key={String(row.governorate_code)}><td>{String(row.governorate_name)}</td><td>{String(row.demand_positions)}</td><td>{String(row.published_offers)}</td></tr>)}</tbody></table>{!labourMarket.demand_by_governorate.length && <p>Aucune demande publiée pendant cette période.</p>}</div></section><section><h4>Métiers à tension élevée</h4><div className="ministry-table-wrap"><table className="ministry-table"><thead><tr><th>Métier</th><th>Gouvernorat</th><th>Postes</th><th>Viviers</th><th>Ratio</th><th>Évolution</th></tr></thead><tbody>{labourMarket.occupations_under_tension.map((row, index) => <tr key={`${String(row.occupation_code)}-${String(row.governorate_code)}-${index}`}><td>{String(row.occupation_title)}<small className="ministry-cell-subtitle">{String(row.occupation_code)}</small></td><td>{String(row.governorate_name)}</td><td>{String(row.demand_positions)}</td><td>{String(row.candidate_supply)}</td><td>{String(row.demand_supply_ratio)}</td><td>{row.demand_change_percent == null ? '—' : `${String(row.demand_change_percent)}%`}</td></tr>)}</tbody></table>{!labourMarket.occupations_under_tension.length && <p>Aucune donnée de tension disponible.</p>}</div></section></div>}
      {section === 'monitoring' && overview && <div className="ministry-metrics-row"><div><span>Requêtes</span><strong>{overview.requests_total}</strong></div><div><span>Refus d’accès</span><strong>{overview.refusals_total}</strong></div><div><span>Temps de fonctionnement</span><strong>{Math.floor(overview.uptime_seconds / 3600)} h</strong></div></div>}
      {section === 'monitoring' && !loading && !error && <section className="ministry-monitoring-panel" aria-label="Qualité du référentiel"><h4>Qualité du référentiel</h4><TaxonomyQuality stats={monitoring.taxonomy} error={monitoring.taxonomyError} /></section>}
      {section === 'monitoring' && !loading && !error && <section className="ministry-monitoring-panel" aria-label="Trafic par route"><h4>Trafic par route</h4><RouteTraffic routes={monitoring.routes} error={monitoring.routesError} /></section>}

      {section === 'suggestions' && rows?.length ? <div className="ministry-review-layout">
        <div className="ministry-suggestion-list" aria-label="Propositions à examiner">{filteredRows.map((row) => <button key={value(row, 'suggestion_id')} type="button" className={`ministry-suggestion${selected?.suggestion_id === row.suggestion_id ? ' selected' : ''}`} onClick={() => { setSelected(row); setSkillLabel(value(row, 'proposed_label')); setSkillCode(''); setMergeCode(''); setRejectReason('') }}><span className="suggestion-type">{value(row, 'skill_type')}</span><strong>{value(row, 'proposed_label')}</strong><small>{value(row, 'source')} · {value(row, 'occurrences')} occurrence(s)</small><span className="module-tag">{value(row, 'status')}</span></button>)}</div>
        <div className="ministry-review-detail">{selected ? <><p className="eyebrow">Proposition sélectionnée</p><h4>{value(selected, 'proposed_label')}</h4><dl><div><dt>Libellé normalisé</dt><dd>{value(selected, 'normalized_label')}</dd></div><div><dt>Origine</dt><dd>{value(selected, 'source')}</dd></div><div><dt>Occurrences signalées</dt><dd>{value(selected, 'occurrences')}</dd></div><div><dt>Type</dt><dd>{value(selected, 'skill_type')}</dd></div></dl><form className="ministry-decision-form" onSubmit={(event) => void reviewSuggestion('approve', event)}><h5>Homologuer comme nouvelle compétence</h5><label>Code REM<input required minLength={2} maxLength={32} value={skillCode} onChange={(event) => setSkillCode(event.target.value.toUpperCase())} placeholder="REM-E1204" /></label><label>Libellé français<input required maxLength={200} value={skillLabel} onChange={(event) => setSkillLabel(event.target.value)} /></label><label>Catégorie<select value={skillType} onChange={(event) => setSkillType(event.target.value)}><option value="hard">Technique / métier</option><option value="soft">Transversale</option><option value="language">Langue</option></select></label><button className="primary-btn" type="submit" disabled={busy}>{busy ? 'Enregistrement…' : 'Homologuer comme brouillon'}</button></form><form className="ministry-merge-form" onSubmit={(event) => void reviewSuggestion('merge', event)}><label>Fusionner dans un code existant<input required value={mergeCode} onChange={(event) => setMergeCode(event.target.value.toUpperCase())} placeholder="Code de la compétence cible" /></label><button className="secondary-btn" type="submit" disabled={busy}>Fusionner</button></form><form className="ministry-reject-form" onSubmit={(event) => void reviewSuggestion('reject', event)}><label>Motif officiel du rejet<textarea required minLength={3} maxLength={1000} value={rejectReason} onChange={(event) => setRejectReason(event.target.value)} /></label><button className="danger-text-btn" type="submit" disabled={busy || rejectReason.trim().length < 3}>Rejeter la proposition</button></form></> : <div className="ministry-empty-selection"><span aria-hidden="true">⌁</span><strong>Sélectionnez une proposition</strong><p>Les détails et les décisions disponibles apparaîtront ici.</p></div>}</div>
      </div> : <>
        {rows && <div className="ministry-list-toolbar"><label className="ministry-search"><span aria-hidden="true">⌕</span><input aria-label="Rechercher dans les résultats" placeholder="Rechercher par libellé, code ou statut…" value={query} onChange={(event) => setQuery(event.target.value)} /></label><span>{filteredRows.length} résultat(s) affiché(s)</span></div>}
        {loading && <div className="ministry-loading" role="status"><span className="loading-line" /><span className="loading-line" /><span className="loading-line short" />Chargement des données…</div>}
        {!loading && !error && rows && filteredRows.length > 0 && <div className="ministry-table-wrap"><table className="ministry-table"><thead><tr>{Object.keys(filteredRows[0]).map((key) => <th key={key} scope="col">{key.replaceAll('_', ' ')}</th>)}{taxonomyKind && <th scope="col">Actions</th>}{section === 'ingestion' && <th scope="col">Rapport</th>}</tr></thead><tbody>{filteredRows.map((row, index) => <tr key={rowKey(row, index)}>{Object.keys(filteredRows[0]).map((key) => <td key={key}>{value(row, key)}</td>)}{taxonomyKind && <td>{taxonomyActions(taxonomyKind, row)}</td>}{section === 'ingestion' && <td>{jobAction(row)}</td>}</tr>)}</tbody></table></div>}
        {!loading && !error && rows && filteredRows.length === 0 && <div className="ministry-empty-selection"><strong>{query ? 'Aucun résultat correspondant' : 'Aucun enregistrement'}</strong><p>{query ? 'Modifiez la recherche pour afficher d’autres résultats.' : 'Les enregistrements apparaîtront ici après leur dépôt ou leur transmission.'}</p></div>}
        {!loading && !error && !rows && data && section !== 'labour-market' && <pre className="ministry-json">{JSON.stringify(data, null, 2)}</pre>}
        {data && typeof data === 'object' && 'page' in data && 'page_size' in data && total > (data.page_size as number) && <div className="ministry-pagination"><button className="secondary-btn" type="button" disabled={page <= 1 || loading} onClick={() => setPage((current) => current - 1)}>← Précédent</button><span>Page {page} sur {Math.ceil(total / (data.page_size as number))}</span><button className="secondary-btn" type="button" disabled={page * (data.page_size as number) >= total || loading} onClick={() => setPage((current) => current + 1)}>Suivant →</button></div>}
      </>}
      {section === 'ingestion' && <p className="ministry-footnote"><button className="secondary-btn" type="button" onClick={() => void queueMarketRefresh()} disabled={busy || loading}>{busy ? 'Mise en file…' : 'Lancer l’actualisation officielle'}</button><span>La demande est enregistrée dans la file durable. Le worker doit être actif et la source officielle configurée pour terminer le traitement.</span></p>}
      {section === 'datasets' && <section className="market-upload-panel"><h4>Déposer un fichier CSV ou XLSX</h4><p>Colonnes requises : indicator_type, period_start, period_end, value, unit. Codes occupation_code, skill_code, sector_code et governorate_code sont facultatifs; extra doit être un objet JSON. Le fichier est stocké dans un bucket privé et supprimé si la prévisualisation expire sans confirmation.</p><form onSubmit={(event) => void previewMarketUpload(event)} className="market-upload-form"><label>Nom du jeu<input required minLength={3} maxLength={200} value={marketTitle} onChange={(event) => setMarketTitle(event.target.value)} /></label><label>Source officielle<input required minLength={2} maxLength={200} value={marketPublisher} onChange={(event) => setMarketPublisher(event.target.value)} /></label><label>Début de période<input required type="date" value={marketPeriodStart} onChange={(event) => setMarketPeriodStart(event.target.value)} /></label><label>Fin de période<input required type="date" value={marketPeriodEnd} onChange={(event) => setMarketPeriodEnd(event.target.value)} /></label><label>Fichier<input required type="file" accept=".csv,.xlsx" onChange={(event) => setMarketFile(event.target.files?.[0] ?? null)} /></label><button className="secondary-btn" type="submit" disabled={busy || !marketFile}>{busy ? 'Vérification…' : 'Prévisualiser et valider'}</button></form>{uploadPreview && <div className="market-upload-preview"><h5>Prévisualisation</h5><p>{uploadPreview.records_valid} lignes valides sur {uploadPreview.records_total}; {uploadPreview.records_invalid} rejet(s). Expire {new Date(uploadPreview.expires_at).toLocaleString()}.</p><details><summary>Exemples de lignes valides ({uploadPreview.sample.length})</summary><pre className="ministry-json">{JSON.stringify(uploadPreview.sample, null, 2)}</pre></details>{uploadPreview.rejections.length > 0 && <><label className="consent-checkbox"><input type="checkbox" checked={acceptValidRows} onChange={(event) => setAcceptValidRows(event.target.checked)} />Importer les lignes valides et ignorer explicitement les lignes rejetées.</label><ul>{uploadPreview.rejections.slice(0, 10).map((item) => <li key={item.index}>Ligne {item.index + 2}: {item.reason}</li>)}</ul></>}<button className="primary-btn" type="button" onClick={() => void confirmMarketUpload()} disabled={busy || (uploadPreview.records_invalid > 0 && !acceptValidRows)}>{busy ? 'Importation…' : 'Confirmer le dépôt'}</button></div>}</section>}
      {section === 'analytics' && <p className="ministry-footnote">Skill gap detail remains available here. The regional overview and export use the dedicated aggregated endpoint.</p>}
      {section === 'labour-market' && <p className="ministry-footnote"><button className="secondary-btn" type="button" onClick={() => void downloadLabourMarketCsv()} disabled={exporting}>{exporting ? 'Préparation…' : 'Exporter le rapport agrégé (CSV)'}</button><button className="secondary-btn" type="button" onClick={() => void downloadLabourMarketPdf()} disabled={exporting}>{exporting ? 'Préparation…' : 'Exporter le rapport agrégé (PDF)'}</button></p>}
      {section === 'monitoring' && <p className="ministry-footnote">Les compteurs de requêtes sont conservés en mémoire et repartent à zéro au redémarrage du service.</p>}
    </section>
  </main>
}
