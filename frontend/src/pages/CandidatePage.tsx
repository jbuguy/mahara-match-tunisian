import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, useLocation } from 'react-router-dom'

import { requestJson } from '../lib/api'

type Identity = { email: string; name: string | null; has_profile: boolean }
type Governorate = { code: string; name_fr: string; name_ar: string }
type ProfileSkill = { code: string; level: number; source: 'self_declared' | 'cv'; confidence: number | null }
type ProfileExperience = { job_title_raw: string; employer_name: string | null; start_date: string | null; end_date: string | null; duration_months: number | null; description: string | null }
type ProfileEducation = { level: string | null; field_of_study: string | null; institution: string | null; graduation_year: number | null }
type Profile = {
  full_name: string | null
  phone: string | null
  governorate: Governorate | null
  literacy_level: string
  education_level: string | null
  years_experience: number | null
  available_from: string | null
  summary: string | null
  consent_given_at: string | null
  languages: { code: string; level: string }[]
  skills: (ProfileSkill & { label_fr: string })[]
  experiences: (ProfileExperience & { id: string })[]
  educations: (ProfileEducation & { id: string })[]
  desired_occupations: { code: string; priority: number | null }[]
}
type CvDraft = {
  draft: {
    full_name: string
    email: string
    phone: string
    education_level: string
    skills: { code: string; level: number; source: 'cv'; confidence: number | null }[]
    experiences: { job_title_raw: string; employer_name: string; start_date: string; end_date: string; duration_months: string; description: string }[]
    educations: ProfileEducation[]
  }
  unmatched_words: string[]
}
type AssistantMessage = { role: 'user' | 'assistant'; content: string }
type AssistantAnswer = {
  reply: string
  done: boolean
  unmatched: string[]
  updates: {
    full_name?: string | null
    phone?: string | null
    governorate_code?: string | null
    education_level?: string | null
    skills?: { code: string; level: number; source: 'cv'; confidence: number | null }[] | null
    experiences?: CvDraft['draft']['experiences'] | null
    desired_occupations?: { code: string; title_fr: string }[] | null
    languages?: { code: string; level: string }[] | null
    summary?: string | null
  }
}

const educationOptions = [
  ['none', 'No formal education'], ['primary', 'Primary'], ['lower_secondary', 'Lower secondary'],
  ['baccalaureate', 'Baccalaureate'], ['vocational_cap', 'CAP'], ['vocational_btp', 'BTP'],
  ['vocational_bts', 'BTS'], ['licence', 'Licence'], ['master', 'Master'],
  ['engineer', 'Engineer'], ['doctorate', 'Doctorate'],
]

export function CandidatePage() {
  const location = useLocation()
  const onboardingDraft = (location.state as { wp2Draft?: {
    jobTitle?: string
    availableFrom?: string | null
    governorateCode?: string | null
    phone?: string | null
  } } | null)?.wp2Draft
  const [identity, setIdentity] = useState<Identity | null>(null)
  const [governorates, setGovernorates] = useState<Governorate[]>([])
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [governorateCode, setGovernorateCode] = useState('')
  const [literacyLevel, setLiteracyLevel] = useState('literate')
  const [educationLevel, setEducationLevel] = useState('')
  const [yearsExperience, setYearsExperience] = useState('')
  const [availableFrom, setAvailableFrom] = useState('')
  const [summary, setSummary] = useState('')
  const [consentGiven, setConsentGiven] = useState(false)
  const [fromCv, setFromCv] = useState(false)
  const [languages, setLanguages] = useState<Profile['languages']>([])
  const [skills, setSkills] = useState<ProfileSkill[]>([])
  const [experiences, setExperiences] = useState<ProfileExperience[]>([])
  const [educations, setEducations] = useState<ProfileEducation[]>([])
  const [desiredOccupations, setDesiredOccupations] = useState<Profile['desired_occupations']>([])
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [importingCv, setImportingCv] = useState(false)
  const [assistantMessages, setAssistantMessages] = useState<AssistantMessage[]>([])
  const [assistantInput, setAssistantInput] = useState('')
  const [assistantError, setAssistantError] = useState('')
  const [assistantPending, setAssistantPending] = useState(false)

  useEffect(() => {
    let active = true
    async function loadProfile() {
      try {
        const [me, locations] = await Promise.all([
          requestJson<Identity>('/api/v1/me'),
          requestJson<Governorate[]>('/api/v1/reference/governorates'),
        ])
        if (!active) return
        setIdentity(me)
        setGovernorates(locations)
        setFullName(me.name ?? '')
        try {
          const profile = await requestJson<Profile>('/api/v1/me/profile')
          if (!active) return
          setFullName(profile.full_name ?? me.name ?? '')
          setPhone(profile.phone ?? '')
          setGovernorateCode(profile.governorate?.code ?? '')
          setLiteracyLevel(profile.literacy_level)
          setEducationLevel(profile.education_level ?? '')
          setYearsExperience(profile.years_experience?.toString() ?? '')
          setAvailableFrom(profile.available_from ?? '')
          setSummary(profile.summary ?? '')
          setConsentGiven(Boolean(profile.consent_given_at))
          setLanguages(profile.languages)
          setSkills(profile.skills.map(({ code, level, source, confidence }) => ({ code, level, source, confidence })))
          setExperiences(profile.experiences.map(({ id: _id, ...experience }) => experience))
          setEducations(profile.educations.map(({ id: _id, ...education }) => education))
          setDesiredOccupations(profile.desired_occupations)
        } catch (profileError) {
          if (!(profileError instanceof Error) || profileError.message !== 'profile not found') throw profileError
        }
        if (onboardingDraft) {
          if (onboardingDraft.phone) setPhone(onboardingDraft.phone)
          if (onboardingDraft.governorateCode) setGovernorateCode(onboardingDraft.governorateCode)
          if (onboardingDraft.availableFrom) setAvailableFrom(onboardingDraft.availableFrom)
          if (onboardingDraft.jobTitle) {
            setSummary((current) => current || `Métier indiqué à l'accueil : ${onboardingDraft.jobTitle}`)
          }
        }
      } catch (loadError) {
        if (active) setError(loadError instanceof Error ? loadError.message : 'Could not load your profile.')
      } finally {
        if (active) setLoading(false)
      }
    }
    void loadProfile()
    return () => { active = false }
  }, [])

  async function importCv(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    setImportingCv(true)
    setError('')
    setNotice('')
    try {
      const body = new FormData()
      body.append('file', file)
      const imported = await requestJson<CvDraft>('/api/v1/me/cv', { method: 'POST', body })
      const draft = imported.draft
      if (draft.full_name) setFullName(draft.full_name)
      if (draft.phone) setPhone(draft.phone)
      if (draft.education_level) setEducationLevel(draft.education_level)
      if (draft.skills.length) setSkills(draft.skills)
      if (draft.experiences.length) {
        setExperiences(draft.experiences.map((experience) => ({
          ...experience,
          start_date: experience.start_date || null,
          end_date: experience.end_date || null,
          duration_months: experience.duration_months ? Number(experience.duration_months) : null,
          description: experience.description || null,
        })))
      }
      if (draft.educations.length) setEducations(draft.educations)
      setFromCv(true)
      setNotice(imported.unmatched_words.length
        ? `CV imported for review. Some terms were not matched: ${imported.unmatched_words.join(', ')}`
        : 'CV imported. Review the extracted details before saving.')
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : 'Could not import this CV.')
    } finally {
      setImportingCv(false)
      event.target.value = ''
    }
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await requestJson('/api/v1/me/profile', {
        method: 'PUT',
        body: JSON.stringify({
          consent: consentGiven,
          from_cv: fromCv,
          full_name: fullName,
          email: identity?.email,
          phone: phone || null,
          governorate_code: governorateCode || null,
          literacy_level: literacyLevel,
          education_level: educationLevel || null,
          years_experience: yearsExperience === '' ? null : Number(yearsExperience),
          available_from: availableFrom || null,
          summary: summary || null,
          languages,
          skills,
          experiences,
          educations,
          desired_occupations: desiredOccupations,
        }),
      })
      setNotice('Your profile has been saved.')
      setIdentity((current) => current ? { ...current, has_profile: true } : current)
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save your profile.')
    } finally {
      setSaving(false)
    }
  }

  async function askAssistant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!assistantInput.trim()) return
    const messages = [...assistantMessages, { role: 'user' as const, content: assistantInput.trim() }]
    setAssistantPending(true)
    setAssistantError('')
    try {
      const answer = await requestJson<AssistantAnswer>('/api/v1/me/assistant/chat', {
        method: 'POST',
        body: JSON.stringify({
          messages,
          draft: {
            full_name: fullName,
            phone,
            governorate_code: governorateCode,
            education_level: educationLevel,
            summary,
            skills: skills.map(({ code, level }) => ({ code, level })),
            experiences: experiences.map((item) => ({
              job_title_raw: item.job_title_raw,
              employer_name: item.employer_name ?? '',
              start_date: item.start_date ?? '',
              end_date: item.end_date ?? '',
              duration_months: item.duration_months?.toString() ?? '',
            })),
            desired_occupations: desiredOccupations.map(({ code }) => ({ code })),
            languages: languages.map(({ code, level }) => ({ code, level })),
          },
        }),
      })
      const updates = answer.updates
      if (updates.full_name) setFullName(updates.full_name)
      if (updates.phone) setPhone(updates.phone)
      if (updates.governorate_code) setGovernorateCode(updates.governorate_code)
      if (updates.education_level) setEducationLevel(updates.education_level)
      if (updates.summary) setSummary(updates.summary)
      if (updates.skills) setSkills(updates.skills)
      if (updates.experiences) setExperiences(updates.experiences.map((item) => ({
        ...item,
        start_date: item.start_date || null,
        end_date: item.end_date || null,
        duration_months: item.duration_months ? Number(item.duration_months) : null,
        description: item.description || null,
      })))
      if (updates.desired_occupations) setDesiredOccupations(updates.desired_occupations.map((item, index) => ({ code: item.code, priority: index + 1 })))
      if (updates.languages) setLanguages(updates.languages)
      setAssistantMessages([...messages, { role: 'assistant', content: answer.reply }])
      setAssistantInput('')
      if (answer.unmatched.length) setNotice(`Review unmatched terms: ${answer.unmatched.join(', ')}`)
    } catch (assistantRequestError) {
      setAssistantError(assistantRequestError instanceof Error ? assistantRequestError.message : 'The profile assistant is unavailable.')
    } finally {
      setAssistantPending(false)
    }
  }

  if (!localStorage.getItem('mahara_access_token')) {
    return <div className="stacked-view"><h2>Candidate profile</h2><p>Sign in with Google to manage your candidate profile.</p><Link className="primary-btn" to="/signin">Sign in</Link></div>
  }
  if (loading) return <div className="stacked-view"><p>Loading candidate profile…</p></div>

  return (
    <div className="stacked-view">
      <header className="panel-header">
        <div><p className="eyebrow">WP6 · Candidate</p><h2>Your professional profile</h2></div>
        <span className="module-tag">{identity?.has_profile ? 'Profile saved' : 'Profile setup'}</span>
      </header>
      <label className="secondary-btn cv-upload">{importingCv ? 'Reading CV…' : 'Import CV'}<input type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={importCv} disabled={importingCv} /></label>
      <form className="auth-form profile-form" onSubmit={saveProfile}>
        <div className="two-col">
          <label><span>Full name</span><input required value={fullName} onChange={(event) => setFullName(event.target.value)} /></label>
          <label><span>Phone</span><input type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} /></label>
        </div>
        <div className="two-col">
          <label><span>Governorate</span><select value={governorateCode} onChange={(event) => setGovernorateCode(event.target.value)}><option value="">Select a governorate</option>{governorates.map((place) => <option key={place.code} value={place.code}>{place.name_fr}</option>)}</select></label>
          <label><span>Literacy level</span><select value={literacyLevel} onChange={(event) => setLiteracyLevel(event.target.value)}><option value="literate">Literate</option><option value="basic">Basic</option><option value="non_literate">Non-literate</option></select></label>
        </div>
        <div className="two-col">
          <label><span>Education</span><select value={educationLevel} onChange={(event) => setEducationLevel(event.target.value)}><option value="">Not specified</option>{educationOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label><span>Years of experience</span><input type="number" min="0" max="80" value={yearsExperience} onChange={(event) => setYearsExperience(event.target.value)} /></label>
        </div>
        <label><span>Available from</span><input type="date" value={availableFrom} onChange={(event) => setAvailableFrom(event.target.value)} /></label>
        <label><span>Professional summary</span><textarea rows={4} value={summary} onChange={(event) => setSummary(event.target.value)} /></label>
        <label className="consent-control"><input required type="checkbox" checked={consentGiven} onChange={(event) => setConsentGiven(event.target.checked)} /><span>I consent to Mahara Match storing and using this information to support my job search.</span></label>
        {notice && <p className="form-notice" role="status">{notice}</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-btn" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save profile'}</button>
      </form>
      <section className="detail-panel assistant-chat">
        <div><p className="eyebrow">WP6 · Profile assistant</p><h3>Get help completing your profile</h3></div>
        <div className="assistant-transcript" aria-live="polite">{assistantMessages.map((item, index) => <div className={`conversation-message ${item.role}`} key={`${index}-${item.role}`}><span>{item.role === 'assistant' ? 'Mahara' : 'You'}</span><p>{item.content}</p></div>)}{assistantMessages.length === 0 && <p>Ask for help describing your experience, skills, or next career step.</p>}</div>
        <form className="conversation-form" onSubmit={askAssistant}><textarea aria-label="Message to profile assistant" rows={2} value={assistantInput} onChange={(event) => setAssistantInput(event.target.value)} placeholder="Write in French, Arabic, or Derja…" required /><button className="secondary-btn" type="submit" disabled={assistantPending || !assistantInput.trim()}>{assistantPending ? 'Thinking…' : 'Ask assistant'}</button></form>
        {assistantError && <p className="form-error" role="alert">{assistantError}</p>}
      </section>
    </div>
  )
}
