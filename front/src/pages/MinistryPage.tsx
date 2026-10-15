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

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const endpoint = sections.find((item) => item.id === section)!.endpoint.replace('page=1', `page=${page}`)
      const result = await requestJson<unknown>(endpoint)
      setData(result)
      if (section === 'analytics') setAnalytics(result as SkillGapMap)
      if (section === 'monitoring') setOverview(result as Overview)
      if (section === 'labour-market') setLabourMarket(result as LabourMarket)
    } catch (cause) {
      setData(null)
      setError(cause instanceof Error ? cause.message : 'Impossible de charger les données ministérielles.')
    } finally {
      setLoading(false)
    }
  }, [section, page])

  useEffect(() => { void load(); setSelected(null); setQuery('') }, [load])
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
        <div className="ministry-heading-actions"><span className="ministry-record-count">{loading ? 'Chargement…' : `${total} enregistrement${total === 1 ? '' : 's'}`}</span><button className="ghost-btn" type="button" onClick={() => void load()} disabled={loading || busy}>↻ Actualiser</button></div>
      </div>

      {error && <div className="ministry-alert error" role="alert"><strong>{error.includes('403') || error.includes('401') ? 'Accès réservé' : 'La requête a échoué'}</strong><span>{error.includes('403') || error.includes('401') ? 'Votre compte ne dispose pas des privilèges requis pour cette section.' : error}</span><button className="secondary-btn" type="button" onClick={() => void load()} disabled={loading}>Réessayer</button></div>}
      {notice && <p className="form-notice" role="status">{notice}</p>}

      {section === 'analytics' && analytics && <div className="ministry-privacy-note"><strong>Données agrégées et anonymisées</strong><span>{analytics.cells_suppressed} cellule(s) supprimée(s) sous le seuil de confidentialité k={analytics.k_anonymity}. Aucun dossier candidat individuel n’est affiché.</span></div>}
      {section === 'labour-market' && labourMarket && <div className="ministry-privacy-note"><strong>Données agrégées et anonymisées</strong><span>{labourMarket.cells_suppressed} cellule(s) supprimée(s), seuil k={labourMarket.k_anonymity}. Ratio version {labourMarket.definition_version}. Période de comparaison : {labourMarket.comparison_period_start} – {labourMarket.comparison_period_end}.</span></div>}
      {section === 'labour-market' && labourMarket && <div className="ministry-market-grid"><section><h4>Demande par gouvernorat</h4><div className="ministry-table-wrap"><table className="ministry-table"><thead><tr><th>Gouvernorat</th><th>Postes</th><th>Offres</th></tr></thead><tbody>{labourMarket.demand_by_governorate.map((row) => <tr key={String(row.governorate_code)}><td>{String(row.governorate_name)}</td><td>{String(row.demand_positions)}</td><td>{String(row.published_offers)}</td></tr>)}</tbody></table>{!labourMarket.demand_by_governorate.length && <p>Aucune demande publiée pendant cette période.</p>}</div></section><section><h4>Métiers à tension élevée</h4><div className="ministry-table-wrap"><table className="ministry-table"><thead><tr><th>Métier</th><th>Gouvernorat</th><th>Postes</th><th>Viviers</th><th>Ratio</th><th>Évolution</th></tr></thead><tbody>{labourMarket.occupations_under_tension.map((row, index) => <tr key={`${String(row.occupation_code)}-${String(row.governorate_code)}-${index}`}><td>{String(row.occupation_title)}<small className="ministry-cell-subtitle">{String(row.occupation_code)}</small></td><td>{String(row.governorate_name)}</td><td>{String(row.demand_positions)}</td><td>{String(row.candidate_supply)}</td><td>{String(row.demand_supply_ratio)}</td><td>{row.demand_change_percent == null ? '—' : `${String(row.demand_change_percent)}%`}</td></tr>)}</tbody></table>{!labourMarket.occupations_under_tension.length && <p>Aucune donnée de tension disponible.</p>}</div></section></div>}
      {section === 'monitoring' && overview && <div className="ministry-metrics-row"><div><span>Requêtes</span><strong>{overview.requests_total}</strong></div><div><span>Refus d’accès</span><strong>{overview.refusals_total}</strong></div><div><span>Temps de fonctionnement</span><strong>{Math.floor(overview.uptime_seconds / 3600)} h</strong></div></div>}

      {section === 'suggestions' && rows?.length ? <div className="ministry-review-layout">
        <div className="ministry-suggestion-list" aria-label="Propositions à examiner">{filteredRows.map((row) => <button key={value(row, 'suggestion_id')} type="button" className={`ministry-suggestion${selected?.suggestion_id === row.suggestion_id ? ' selected' : ''}`} onClick={() => { setSelected(row); setSkillLabel(value(row, 'proposed_label')); setSkillCode(''); setMergeCode(''); setRejectReason('') }}><span className="suggestion-type">{value(row, 'skill_type')}</span><strong>{value(row, 'proposed_label')}</strong><small>{value(row, 'source')} · {value(row, 'occurrences')} occurrence(s)</small><span className="module-tag">{value(row, 'status')}</span></button>)}</div>
        <div className="ministry-review-detail">{selected ? <><p className="eyebrow">Proposition sélectionnée</p><h4>{value(selected, 'proposed_label')}</h4><dl><div><dt>Libellé normalisé</dt><dd>{value(selected, 'normalized_label')}</dd></div><div><dt>Origine</dt><dd>{value(selected, 'source')}</dd></div><div><dt>Occurrences signalées</dt><dd>{value(selected, 'occurrences')}</dd></div><div><dt>Type</dt><dd>{value(selected, 'skill_type')}</dd></div></dl><form className="ministry-decision-form" onSubmit={(event) => void reviewSuggestion('approve', event)}><h5>Homologuer comme nouvelle compétence</h5><label>Code REM<input required minLength={2} maxLength={32} value={skillCode} onChange={(event) => setSkillCode(event.target.value.toUpperCase())} placeholder="REM-E1204" /></label><label>Libellé français<input required maxLength={200} value={skillLabel} onChange={(event) => setSkillLabel(event.target.value)} /></label><label>Catégorie<select value={skillType} onChange={(event) => setSkillType(event.target.value)}><option value="hard">Technique / métier</option><option value="soft">Transversale</option><option value="language">Langue</option></select></label><button className="primary-btn" type="submit" disabled={busy}>{busy ? 'Enregistrement…' : 'Homologuer comme brouillon'}</button></form><form className="ministry-merge-form" onSubmit={(event) => void reviewSuggestion('merge', event)}><label>Fusionner dans un code existant<input required value={mergeCode} onChange={(event) => setMergeCode(event.target.value.toUpperCase())} placeholder="Code de la compétence cible" /></label><button className="secondary-btn" type="submit" disabled={busy}>Fusionner</button></form><form className="ministry-reject-form" onSubmit={(event) => void reviewSuggestion('reject', event)}><label>Motif officiel du rejet<textarea required minLength={3} maxLength={1000} value={rejectReason} onChange={(event) => setRejectReason(event.target.value)} /></label><button className="danger-text-btn" type="submit" disabled={busy || rejectReason.trim().length < 3}>Rejeter la proposition</button></form></> : <div className="ministry-empty-selection"><span aria-hidden="true">⌁</span><strong>Sélectionnez une proposition</strong><p>Les détails et les décisions disponibles apparaîtront ici.</p></div>}</div>
      </div> : <>
        {rows && <div className="ministry-list-toolbar"><label className="ministry-search"><span aria-hidden="true">⌕</span><input aria-label="Rechercher dans les résultats" placeholder="Rechercher par libellé, code ou statut…" value={query} onChange={(event) => setQuery(event.target.value)} /></label><span>{filteredRows.length} résultat(s) affiché(s)</span></div>}
        {loading && <div className="ministry-loading" role="status"><span className="loading-line" /><span className="loading-line" /><span className="loading-line short" />Chargement des données…</div>}
        {!loading && !error && rows && filteredRows.length > 0 && <div className="ministry-table-wrap"><table className="ministry-table"><thead><tr>{Object.keys(filteredRows[0]).map((key) => <th key={key} scope="col">{key.replaceAll('_', ' ')}</th>)}{section === 'skills' && <th scope="col">Action</th>}</tr></thead><tbody>{filteredRows.map((row, index) => <tr key={value(row, 'skill_id') || value(row, 'occupation_id') || value(row, 'dataset_id') || value(row, 'job_id') || String(index)}>{Object.keys(filteredRows[0]).map((key) => <td key={key}>{value(row, key)}</td>)}{section === 'skills' && <td>{row.status === 'draft' && typeof row.code === 'string' ? <button className="secondary-btn" type="button" disabled={busy} onClick={async () => { setBusy(true); try { await requestJson(`/api/v1/admin/taxonomy/skills/${encodeURIComponent(row.code as string)}/validate`, { method: 'POST' }); setNotice(`La compétence ${row.code} a été validée.`); await load() } catch (cause) { setError(cause instanceof Error ? cause.message : 'Validation impossible.') } finally { setBusy(false) } }}>Valider</button> : '—'}</td>}</tr>)}</tbody></table></div>}
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
