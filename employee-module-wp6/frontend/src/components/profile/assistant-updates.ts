/** The profile assistant and the form: the draft it's sent, and merging its updates into the form values. */

import type { AssistantDraft, AssistantUpdates } from '@/lib/api'
import {
  MAX_OCCUPATIONS,
  MAX_SKILLS,
  newExperience,
  newKey,
  type ExperienceValue,
  type ProfileFormValues,
  type SkillValue,
} from './form-values'

/** What the assistant needs to know about the form (the photo, consent and e-mail aren't sent). */
export function toAssistantDraft(values: ProfileFormValues): AssistantDraft {
  return {
    full_name: values.full_name,
    phone: values.phone,
    governorate_code: values.governorate_code,
    education_level: values.education_level,
    skills: values.skills.map(({ code, label_fr, level }) => ({ code, label_fr, level })),
    experiences: values.experiences.map((experience) => {
      const byDates = experience.mode === 'dates'
      return {
        job_title_raw: experience.job_title_raw,
        employer_name: experience.employer_name,
        start_date: byDates ? experience.start_date : '',
        end_date: byDates ? experience.end_date : '',
        duration_months: byDates ? '' : experience.duration_months,
      }
    }),
    desired_occupations: values.desired_occupations,
    languages: values.languages.map(({ code, level }) => ({ code, level })),
    summary: values.summary,
  }
}

/**
 * A changed field: its name (`phone`), or a list item as `kind:id` (`skill:SK-9006`, `experience:row-3`).
 * The form highlights these and the chat says which parts were filled.
 */
export type Change = string

const SCALARS = ['full_name', 'phone', 'governorate_code', 'education_level', 'summary'] as const

/** Lower-case without accents, to recognise a job that's already in the form. */
function folded(text: string): string {
  return text.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().trim()
}

/**
 * Merges the assistant's updates into the form values. Nothing is ever removed: fields are replaced,
 * skills and languages get their new level, jobs with the same title are completed, new items are added.
 */
export function mergeAssistantUpdates(
  values: ProfileFormValues,
  updates: AssistantUpdates,
): { values: ProfileFormValues; changed: Change[] } {
  const next = { ...values }
  const changed: Change[] = []

  for (const field of SCALARS) {
    const value = updates[field]
    if (value != null && value !== values[field]) {
      next[field] = value
      changed.push(field)
    }
  }

  if (updates.skills?.length) {
    let skills = values.skills
    const added: SkillValue[] = []
    for (const skill of updates.skills) {
      const current = skills.find((item) => item.code === skill.code)
      if (current) {
        if (current.level === skill.level) continue
        skills = skills.map((item) => (item.code === skill.code ? { ...item, level: skill.level } : item))
      } else if (skills.length + added.length < MAX_SKILLS) {
        added.push({ code: skill.code, label_fr: skill.label_fr, level: skill.level, source: 'self_declared', confidence: null })
      } else continue
      changed.push(`skill:${skill.code}`)
    }
    next.skills = [...added, ...skills] // new skills on top, as when the candidate adds one
  }

  if (updates.experiences?.length) {
    const experiences = [...values.experiences]
    for (const job of updates.experiences) {
      // The same job told in two answers ("soudeur", then "3 ans chez STEG") completes the first one.
      const index = experiences.findIndex(
        (item) =>
          folded(item.job_title_raw) === folded(job.job_title_raw) &&
          (!item.employer_name.trim() || !job.employer_name || folded(item.employer_name) === folded(job.employer_name)),
      )
      if (index < 0) {
        const row: ExperienceValue = {
          ...newExperience(),
          job_title_raw: job.job_title_raw,
          employer_name: job.employer_name,
          duration_months: job.duration_months,
          mode: job.duration_months ? 'duration' : 'dates',
        }
        experiences.push(row)
        changed.push(`experience:${row.key}`)
        continue
      }
      const current = experiences[index]
      const patch: Partial<ExperienceValue> = {}
      if (job.employer_name && !current.employer_name.trim()) patch.employer_name = job.employer_name
      if (job.duration_months && !current.start_date && job.duration_months !== current.duration_months) {
        patch.duration_months = job.duration_months
        patch.mode = 'duration'
      }
      if (Object.keys(patch).length > 0) {
        experiences[index] = { ...current, ...patch }
        changed.push(`experience:${current.key}`)
      }
    }
    next.experiences = experiences
  }

  if (updates.desired_occupations?.length) {
    const occupations = [...values.desired_occupations]
    for (const occupation of updates.desired_occupations) {
      if (occupations.length >= MAX_OCCUPATIONS || occupations.some((item) => item.code === occupation.code)) continue
      occupations.push({ code: occupation.code, title_fr: occupation.title_fr })
      changed.push(`occupation:${occupation.code}`)
    }
    next.desired_occupations = occupations
  }

  if (updates.languages?.length) {
    const languages = [...values.languages]
    for (const language of updates.languages) {
      const index = languages.findIndex((item) => item.code === language.code)
      if (index < 0) {
        const row = { key: newKey(), code: language.code, level: language.level }
        languages.push(row)
        changed.push(`language:${row.key}`)
      } else if (languages[index].level !== language.level) {
        languages[index] = { ...languages[index], level: language.level }
        changed.push(`language:${languages[index].key}`)
      }
    }
    next.languages = languages
  }

  return { values: next, changed }
}

const KINDS: Record<string, { field: keyof ProfileFormValues; label: string; step: number }> = {
  full_name: { field: 'full_name', label: 'Nom complet', step: 0 },
  phone: { field: 'phone', label: 'Téléphone', step: 0 },
  governorate_code: { field: 'governorate_code', label: 'Gouvernorat', step: 0 },
  education_level: { field: 'education_level', label: "Niveau d'études", step: 0 },
  skill: { field: 'skills', label: 'Compétences', step: 1 },
  experience: { field: 'experiences', label: 'Expériences', step: 2 },
  occupation: { field: 'desired_occupations', label: 'Métiers souhaités', step: 2 },
  language: { field: 'languages', label: 'Langues', step: 2 },
  summary: { field: 'summary', label: 'À propos', step: 2 },
}

function kindOf(change: Change) {
  return KINDS[change.split(':')[0]]
}

/** The form fields these changes touch (`skill:SK-1` → `skills`). */
export function changedFields(changes: Change[]): (keyof ProfileFormValues)[] {
  return [...new Set(changes.map((change) => kindOf(change).field))]
}

/** French names of what was filled, for the chat: ["Nom complet", "Compétences"]. */
export function changedLabels(changes: Change[]): string[] {
  return [...new Set(changes.map((change) => kindOf(change).label))]
}

/** The form step that shows these changes (the furthest one: the conversation goes through the steps in order). */
export function stepOfChanges(changes: Change[]): number {
  return Math.max(...changes.map((change) => kindOf(change).step))
}

/** The form step that shows this field (`skills` → 1), or null for an unknown one. */
export function stepOfField(field: string): number | null {
  return Object.values(KINDS).find((kind) => kind.field === field)?.step ?? null
}
