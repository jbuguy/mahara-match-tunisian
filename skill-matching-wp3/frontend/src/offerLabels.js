export function titreOffre(offre, numero = 1) {
  const skills = offre?.skills || []
  const required = skills
    .filter((skill) => skill.requirement === 'required')
    .map((skill) => skill.label_raw)
    .filter(Boolean)
  const title = (required.length ? required : skills.map((skill) => skill.label_raw).filter(Boolean))
    .slice(0, 3)
    .join(' · ')
  return title || `Offre ${numero}`
}

export function libelleCompetence(gap, skillLabels = {}) {
  if (gap?.label_raw) return gap.label_raw
  const code = gap?.skill_code
  if (!code) return 'Compétence'
  if (skillLabels[code]) return skillLabels[code]
  if (code.startsWith('UNMAPPED:')) return code.slice('UNMAPPED:'.length).trim()
  return code
}
