import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { requestJson } from '../lib/api'

type Tab = 'skills' | 'suggestions' | 'occupations' | 'datasets' | 'ingestion' | 'analytics' | 'monitoring'
type Page<T> = { items: T[]; total: number; page: number; page_size: number }
type Row = Record<string, unknown>

const tabs: { id: Tab; label: string; endpoint: string }[] = [
  { id: 'skills', label: 'Skills', endpoint: '/api/v1/admin/taxonomy/skills?page=1&page_size=50' },
  { id: 'suggestions', label: 'Suggestions', endpoint: '/api/v1/admin/taxonomy/suggestions?page=1&page_size=50' },
  { id: 'occupations', label: 'Occupations', endpoint: '/api/v1/admin/taxonomy/occupations?page=1&page_size=50' },
  { id: 'datasets', label: 'Market datasets', endpoint: '/api/v1/admin/market/datasets?page=1&page_size=50' },
  { id: 'ingestion', label: 'Ingestion jobs', endpoint: '/api/v1/admin/ingestion/jobs?page=1&page_size=50' },
  { id: 'analytics', label: 'Skill gaps', endpoint: '/api/v1/admin/analytics/skill-gaps' },
  { id: 'monitoring', label: 'Monitoring', endpoint: '/api/v1/admin/monitoring/overview' },
]

function readable(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export function MinistryPage() {
  const [tab, setTab] = useState<Tab>('skills')
  const [data, setData] = useState<Page<Row> | Row | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await requestJson<Page<Row> | Row>(tabs.find((item) => item.id === tab)!.endpoint))
    } catch (cause) {
      setData(null)
      setError(cause instanceof Error ? cause.message : 'Could not load ministry data.')
    } finally {
      setLoading(false)
    }
  }, [tab])

  useEffect(() => { void load() }, [load])

  async function validateSkill(code: string) {
    setBusy(code)
    setError(null)
    try {
      await requestJson(`/api/v1/admin/taxonomy/skills/${encodeURIComponent(code)}/validate`, { method: 'POST' })
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not validate the skill.')
    } finally {
      setBusy(null)
    }
  }

  const rows = data && 'items' in data && Array.isArray(data.items) ? data.items : null
  const columns = rows?.length ? Object.keys(rows[0]) : []
  const heading = tabs.find((item) => item.id === tab)!.label

  if (!localStorage.getItem('mahara_access_token')) {
    return <section className="stacked-view"><h2>Ministry workspace</h2><p>Sign in with an authorized ministry account to continue.</p><Link className="primary-btn" to="/signin">Sign in</Link></section>
  }

  return <section className="stacked-view ministry-workspace">
    <header className="panel-header">
      <div><p className="eyebrow">Administration</p><h2>Ministry workspace</h2><p>Manage referentials and review labour-market data.</p></div>
      <button className="ghost-btn" type="button" onClick={() => void load()} disabled={loading}>Refresh</button>
    </header>
    <nav className="ministry-tabs" aria-label="Ministry sections">
      {tabs.map((item) => <button key={item.id} type="button" aria-current={tab === item.id ? 'page' : undefined} className={tab === item.id ? 'ministry-tab active' : 'ministry-tab'} onClick={() => setTab(item.id)}>{item.label}</button>)}
    </nav>
    <section className="ministry-results" aria-live="polite">
      <div className="panel-header"><h3>{heading}</h3>{data && 'total' in data && typeof data.total === 'number' && <span className="module-tag">{data.total} records</span>}</div>
      {error && <p className="form-error" role="alert">{error}{error.includes('403') || error.includes('401') ? ' Access is limited to ministry administrators.' : ''}</p>}
      {loading && <p role="status">Loading {heading.toLowerCase()}…</p>}
      {!loading && !error && rows?.length === 0 && <p>No records found.</p>}
      {!loading && !error && rows && rows.length > 0 && <div className="ministry-table-wrap"><table className="ministry-table"><thead><tr>{columns.map((column) => <th key={column} scope="col">{column.replaceAll('_', ' ')}</th>)}{tab === 'skills' && <th scope="col">Action</th>}</tr></thead><tbody>{rows.map((row, index) => <tr key={readable(row.skill_id ?? row.suggestion_id ?? row.occupation_id ?? row.dataset_id ?? row.job_id ?? index)}>{columns.map((column) => <td key={column}>{readable(row[column])}</td>)}{tab === 'skills' && <td>{row.status === 'draft' && typeof row.code === 'string' && <button className="secondary-btn" type="button" disabled={busy === row.code} onClick={() => void validateSkill(row.code as string)}>{busy === row.code ? 'Saving…' : 'Validate'}</button>}</td>}</tr>)}</tbody></table></div>}
      {!loading && !error && !rows && data && <pre className="ministry-json">{JSON.stringify(data, null, 2)}</pre>}
      {tab === 'analytics' && <p className="ministry-note">Small groups are suppressed to protect privacy. No candidate-level records are shown.</p>}
      {tab === 'monitoring' && <p className="ministry-note">Request counters are process-local and reset when the API restarts.</p>}
    </section>
  </section>
}
