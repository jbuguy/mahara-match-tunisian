import { libelleCompetence } from '../offerLabels.js'

function GapChip({ gap, skillLabels }) {
  if (!gap) return <span className="gap-chip acquired">Compétences couvertes</span>
  const label = libelleCompetence(gap, skillLabels)
  const text = gap.gap_type === 'missing'
    ? `${label} · manquante`
    : `${label} · niveau ${gap.current_level}/${gap.required_level}`
  return <span className={`gap-chip ${gap.gap_type === 'missing' ? 'missing' : 'insufficient'}`}>{text}</span>
}

export default GapChip