function GapChip({ gap }) {
  if (!gap) return <span className="gap-chip acquired">Compétences couvertes</span>
  const label = gap.label_raw || gap.skill_code || 'Compétence'
  const text = gap.gap_type === 'missing'
    ? `${label} · manquante`
    : `${label} · niveau ${gap.current_level}/${gap.required_level}`
  return <span className={`gap-chip ${gap.gap_type === 'missing' ? 'missing' : 'insufficient'}`}>{text}</span>
}

export default GapChip