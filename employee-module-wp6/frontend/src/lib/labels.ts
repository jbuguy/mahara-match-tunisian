/** French labels for the codes stored in the database. */

export const EDUCATION_LEVELS: Record<string, string> = {
  none: 'Sans diplôme',
  primary: 'Primaire',
  lower_secondary: 'Collège',
  baccalaureate: 'Baccalauréat',
  vocational_cap: 'CAP (formation professionnelle)',
  vocational_btp: 'BTP (brevet de technicien professionnel)',
  vocational_bts: 'BTS (brevet de technicien supérieur)',
  licence: 'Licence',
  master: 'Master',
  engineer: "Diplôme d'ingénieur",
  doctorate: 'Doctorat',
}

export const SKILL_LEVELS: Record<number, string> = {
  1: 'Débutant',
  2: 'Intermédiaire',
  3: 'Avancé',
  4: 'Expert',
}

export const LANGUAGES: Record<string, string> = {
  ar: 'Arabe',
  fr: 'Français',
  en: 'Anglais',
  de: 'Allemand',
  it: 'Italien',
  es: 'Espagnol',
  tr: 'Turc',
  zh: 'Chinois',
}

export const LANGUAGE_LEVELS: Record<string, string> = {
  basic: 'Notions',
  intermediate: 'Intermédiaire',
  fluent: 'Courant',
  native: 'Langue maternelle',
}

const monthYear = new Intl.DateTimeFormat('fr-FR', { month: 'short', year: 'numeric' })
const dayMonthYear = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })

/** "2024-06-30" → a local Date (no time-zone shift). */
function parseDate(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

export function formatMonthYear(value: string): string {
  return monthYear.format(parseDate(value))
}

export function formatDate(value: string): string {
  return dayMonthYear.format(parseDate(value))
}
