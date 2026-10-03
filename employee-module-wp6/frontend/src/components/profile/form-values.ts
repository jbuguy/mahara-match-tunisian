/** The profile form's state, its conversions to and from the API, and its checks. */

import type { Education, Profile, ProfileIn, ProfileSkill } from '@/lib/api'

export type SkillValue = {
  code: string
  label_fr: string
  level: number
  source: ProfileSkill['source']
  confidence: number | null
}

export type ExperienceValue = {
  /** Local key for React lists; never sent. */
  key: string
  job_title_raw: string
  employer_name: string
  /** The candidate gives either dates or a number of months. */
  mode: 'dates' | 'duration'
  start_date: string
  end_date: string
  duration_months: string
  /** Not editable yet; kept so a save doesn't erase it. */
  description: string
}

export type LanguageValue = { key: string; code: string; level: string }

export type OccupationValue = { code: string; title_fr: string }

export type ProfileFormValues = {
  // Step 1: Infos
  full_name: string
  phone: string
  governorate_code: string
  education_level: string
  // Step 2: Compétences
  skills: SkillValue[]
  // Step 3: Expérience et préférences
  experiences: ExperienceValue[]
  desired_occupations: OccupationValue[]
  available_from: string
  languages: LanguageValue[]
  summary: string
  consent: boolean
  // Not shown in the form, sent back unchanged so a save doesn't erase them.
  email: string
  years_experience: number | null
  educations: Omit<Education, 'id'>[]
}

/**
 * Starting values for the form: any subset, e.g. a CV draft. Experiences and languages
 * may leave out `key` and `mode`; `normalizeValues` fills them in.
 */
export type ProfileFormStart = Partial<Omit<ProfileFormValues, 'experiences' | 'languages'>> & {
  experiences?: (Omit<ExperienceValue, 'key' | 'mode'> & Partial<Pick<ExperienceValue, 'key' | 'mode'>>)[]
  languages?: (Omit<LanguageValue, 'key'> & Partial<Pick<LanguageValue, 'key'>>)[]
}

let lastKey = 0
export function newKey(): string {
  lastKey += 1
  return `row-${lastKey}`
}

export function newExperience(): ExperienceValue {
  return {
    key: newKey(),
    job_title_raw: '',
    employer_name: '',
    mode: 'dates',
    start_date: '',
    end_date: '',
    duration_months: '',
    description: '',
  }
}

export function newLanguage(): LanguageValue {
  return { key: newKey(), code: '', level: 'intermediate' }
}

export function normalizeValues(start: ProfileFormStart = {}): ProfileFormValues {
  return {
    full_name: start.full_name ?? '',
    phone: start.phone ?? '',
    governorate_code: start.governorate_code ?? '',
    education_level: start.education_level ?? '',
    skills: start.skills ?? [],
    experiences: (start.experiences ?? []).map((experience) => ({
      ...experience,
      key: experience.key ?? newKey(),
      mode: experience.mode ?? (experience.duration_months && !experience.start_date ? 'duration' : 'dates'),
    })),
    desired_occupations: start.desired_occupations ?? [],
    available_from: start.available_from ?? '',
    languages: (start.languages ?? []).map((language) => ({ ...language, key: language.key ?? newKey() })),
    summary: start.summary ?? '',
    consent: start.consent ?? false,
    email: start.email ?? '',
    years_experience: start.years_experience ?? null,
    educations: start.educations ?? [],
  }
}

/** Edit mode: the saved profile as form values. */
export function profileToFormValues(profile: Profile): ProfileFormStart {
  return {
    full_name: profile.full_name ?? '',
    phone: profile.phone ?? '',
    governorate_code: profile.governorate?.code ?? '',
    education_level: profile.education_level ?? '',
    skills: profile.skills.map(({ code, label_fr, level, source, confidence }) => ({
      code,
      label_fr,
      level,
      source,
      confidence,
    })),
    experiences: profile.experiences.map((experience) => ({
      job_title_raw: experience.job_title_raw,
      employer_name: experience.employer_name ?? '',
      start_date: experience.start_date ?? '',
      end_date: experience.end_date ?? '',
      duration_months: experience.duration_months?.toString() ?? '',
      description: experience.description ?? '',
    })),
    desired_occupations: profile.desired_occupations.map(({ code, title_fr }) => ({ code, title_fr })),
    available_from: profile.available_from ?? '',
    languages: profile.languages.map(({ code, level }) => ({ code, level })),
    summary: profile.summary ?? '',
    consent: profile.consent_given_at != null,
    email: profile.email ?? '',
    years_experience: profile.years_experience,
    educations: profile.educations.map(({ level, field_of_study, institution, graduation_year }) => ({
      level,
      field_of_study,
      institution,
      graduation_year,
    })),
  }
}

function orNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

/** The PUT /me/profile body. */
export function toProfileIn(values: ProfileFormValues, fromCv: boolean): ProfileIn {
  return {
    consent: values.consent,
    from_cv: fromCv,
    full_name: values.full_name.trim(),
    email: orNull(values.email),
    phone: orNull(values.phone),
    governorate_code: orNull(values.governorate_code),
    education_level: orNull(values.education_level),
    years_experience: values.years_experience,
    languages: values.languages.map(({ code, level }) => ({ code, level })),
    summary: orNull(values.summary),
    available_from: orNull(values.available_from),
    skills: values.skills.map(({ code, level, source, confidence }) => ({ code, level, source, confidence })),
    experiences: values.experiences.map((experience) => {
      const byDates = experience.mode === 'dates'
      return {
        job_title_raw: experience.job_title_raw.trim(),
        employer_name: orNull(experience.employer_name),
        start_date: byDates ? orNull(experience.start_date) : null,
        end_date: byDates ? orNull(experience.end_date) : null,
        duration_months: !byDates && experience.duration_months.trim() ? Number(experience.duration_months) : null,
        description: orNull(experience.description),
      }
    }),
    educations: values.educations,
    desired_occupations: values.desired_occupations.map(({ code }, index) => ({ code, priority: index + 1 })),
  }
}

// ---------------------------------------------------------------------------
// Checks
// ---------------------------------------------------------------------------

/** Error messages by field path, e.g. `phone` or `experiences.0.job_title_raw`. `_form` is for the whole form. */
export type FormErrors = Record<string, string>

export const STEPS = [
  { short: 'Infos', title: 'Vos informations' },
  { short: 'Compétences', title: 'Vos compétences' },
  { short: 'Expérience', title: 'Expérience et préférences' },
] as const

export const SUMMARY_MAX = 500
export const MAX_OCCUPATIONS = 10
export const MAX_SKILLS = 100

/** Tunisian number: 8 digits, optionally after +216 or 00216; spaces, dots and dashes allowed. */
export function isValidPhone(phone: string): boolean {
  return /^(?:\+216|00216)?[2-9]\d{7}$/.test(phone.replace(/[\s.()-]/g, ''))
}

export function validateStep(step: number, values: ProfileFormValues): FormErrors {
  const errors: FormErrors = {}

  if (step === 0) {
    if (!values.full_name.trim()) errors.full_name = 'Indiquez votre nom complet.'
    else if (values.full_name.trim().length > 200) errors.full_name = 'Ce nom est trop long.'
    if (!values.phone.trim()) errors.phone = 'Indiquez votre numéro de téléphone.'
    else if (!isValidPhone(values.phone)) errors.phone = 'Numéro non valide. Exemple : 22 123 456'
    if (!values.governorate_code) errors.governorate_code = 'Choisissez votre gouvernorat.'
  }

  if (step === 1) {
    if (values.skills.length > MAX_SKILLS) errors.skills = `${MAX_SKILLS} compétences au maximum.`
  }

  if (step === 2) {
    values.experiences.forEach((experience, i) => {
      const at = `experiences.${i}`
      if (!experience.job_title_raw.trim()) errors[`${at}.job_title_raw`] = 'Indiquez le poste.'
      if (experience.mode === 'dates') {
        if (experience.start_date && experience.end_date && experience.end_date < experience.start_date) {
          errors[`${at}.end_date`] = 'La date de fin doit être après la date de début.'
        }
      } else if (experience.duration_months.trim()) {
        const months = Number(experience.duration_months)
        if (!Number.isInteger(months) || months < 0 || months > 960) {
          errors[`${at}.duration_months`] = 'Indiquez un nombre de mois, par exemple 12.'
        }
      }
    })
    if (values.desired_occupations.length > MAX_OCCUPATIONS) {
      errors.desired_occupations = `${MAX_OCCUPATIONS} métiers au maximum.`
    }
    const seen = new Set<string>()
    values.languages.forEach((language, i) => {
      if (!language.code) errors[`languages.${i}.code`] = 'Choisissez une langue.'
      else if (seen.has(language.code)) errors[`languages.${i}.code`] = 'Cette langue est déjà dans la liste.'
      seen.add(language.code)
    })
    if (values.summary.trim().length > SUMMARY_MAX) {
      errors.summary = `${SUMMARY_MAX} caractères au maximum.`
    }
    if (!values.consent) errors.consent = 'Cochez cette case pour enregistrer votre profil.'
  }

  return errors
}

const STEP_OF_FIELD: Record<string, number> = {
  full_name: 0,
  phone: 0,
  email: 0,
  governorate_code: 0,
  education_level: 0,
  skills: 1,
}

/** Which step shows the error for this path (errors the form can't place go to the last step). */
export function stepOfError(path: string): number {
  return STEP_OF_FIELD[path.split('.')[0]] ?? 2
}

/**
 * Turns a 422 `detail` (FastAPI's list of `{loc, msg, type}`) into form errors.
 * Returns null when the detail isn't in that shape.
 */
export function serverErrors(detail: unknown): FormErrors | null {
  if (!Array.isArray(detail)) return null
  const errors: FormErrors = {}
  for (const item of detail) {
    const loc: unknown[] = Array.isArray(item?.loc) ? item.loc : []
    const path = loc[0] === 'body' ? loc.slice(1).join('.') : ''
    const message =
      item?.type === 'unknown_code'
        ? "Ce choix n'est plus disponible. Retirez-le."
        : "Cette information n'a pas été acceptée. Vérifiez-la."
    errors[path || '_form'] ??= message
  }
  return errors
}
