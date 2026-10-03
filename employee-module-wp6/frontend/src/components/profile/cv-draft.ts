/** Turns a CV draft (POST /me/cv) into the form's starting values. */

import type { CvDraft, Profile } from '@/lib/api'
import { profileToFormValues, type ProfileFormStart } from './form-values'

/** Lower-case without accents, to spot a job or diploma that's already in the profile. */
function same(...parts: (string | number | null | undefined)[]): string {
  return parts
    .map((part) => String(part ?? '').normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().trim())
    .join('|')
}

/**
 * New profile: the draft, with the Google name if the CV gave none.
 * Existing profile: what's saved stays as it is; the CV only fills empty fields and adds the skills,
 * jobs and diplomas that aren't there yet (so importing a CV never erases anything).
 */
export function draftToFormStart(draft: CvDraft, saved: Profile | null, googleName: string): ProfileFormStart {
  const base: ProfileFormStart = saved ? profileToFormValues(saved) : { full_name: googleName }
  const skills = base.skills ?? []
  const experiences = base.experiences ?? []
  const educations = base.educations ?? []
  const knownSkills = new Set(skills.map((skill) => skill.code))
  const knownJobs = new Set(experiences.map((job) => same(job.job_title_raw, job.employer_name)))
  const knownDiplomas = new Set(educations.map((diploma) => same(diploma.level, diploma.graduation_year)))

  return {
    ...base,
    full_name: (saved && base.full_name) || draft.full_name || base.full_name,
    email: base.email || draft.email,
    phone: base.phone || draft.phone,
    education_level: base.education_level || draft.education_level,
    skills: [...skills, ...draft.skills.filter((skill) => !knownSkills.has(skill.code))],
    experiences: [
      ...experiences,
      ...draft.experiences.filter((job) => !knownJobs.has(same(job.job_title_raw, job.employer_name))),
    ],
    educations: [
      ...educations,
      ...draft.educations.filter((diploma) => !knownDiplomas.has(same(diploma.level, diploma.graduation_year))),
    ],
  }
}
