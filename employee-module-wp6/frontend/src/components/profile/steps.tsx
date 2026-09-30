import { Plus, Trash2 } from 'lucide-react'
import type { ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { searchOccupations, searchSkills, type Governorate } from '@/lib/api'
import { EDUCATION_LEVELS, LANGUAGE_LEVELS, LANGUAGES, SKILL_LEVELS } from '@/lib/labels'
import { cn } from '@/lib/utils'
import { describe, inputClass } from './field-attrs'
import { Field, FieldError, Section, Select } from './fields'
import {
  MAX_OCCUPATIONS,
  MAX_SKILLS,
  SUMMARY_MAX,
  newExperience,
  newLanguage,
  type ExperienceValue,
  type FormErrors,
  type ProfileFormValues,
} from './form-values'
import { PhotoPicker, type PhotoChange } from './PhotoPicker'
import { ReferenceSearch } from './ReferenceSearch'

export type StepProps = {
  values: ProfileFormValues
  errors: FormErrors
  change: (patch: Partial<ProfileFormValues>) => void
}

export type GovernorateList = Governorate[] | 'loading' | 'error'

/** Button with a trash icon and the word "Retirer"; the aria-label says what is removed. */
function RemoveButton({ what, onClick }: { what: string; onClick: () => void }) {
  return (
    <Button
      type="button"
      variant="ghost"
      onClick={onClick}
      aria-label={`Retirer ${what}`}
      className="shrink-0 px-3 text-ink-secondary"
    >
      <Trash2 aria-hidden />
      Retirer
    </Button>
  )
}

/** Buttons that behave like radio choices (aria-pressed), at least 44px high. */
function ChoiceButtons<T extends string | number>({
  label,
  options,
  value,
  onChange,
  className,
}: {
  label: string
  options: { value: T; label: string }[]
  value: T
  onChange: (value: T) => void
  className?: string
}) {
  return (
    <div role="group" aria-label={label} className={cn('grid gap-2', className)}>
      {options.map((option) => {
        const selected = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={selected}
            onClick={() => onChange(option.value)}
            className={cn(
              'min-h-11 rounded-[10px] border px-3 py-2 text-[15px] font-medium transition-colors outline-none focus-visible:ring-3 focus-visible:ring-teal/30',
              selected ? 'border-teal bg-teal text-white' : 'border-line bg-surface text-ink hover:bg-secondary',
            )}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}

function EmptyNote({ children }: { children: ReactNode }) {
  return <p className="rounded-[10px] bg-muted px-4 py-3 text-[15px] text-ink-secondary">{children}</p>
}

// ---------------------------------------------------------------------------
// Step 1: Infos
// ---------------------------------------------------------------------------

export function StepInfos({
  values,
  errors,
  change,
  governorates,
  retryGovernorates,
  photo,
  onPhotoChange,
}: StepProps & {
  governorates: GovernorateList
  retryGovernorates: () => void
  photo: PhotoChange
  onPhotoChange: (change: PhotoChange) => void
}) {
  const sortedGovernorates = Array.isArray(governorates)
    ? [...governorates].sort((a, b) => a.name_fr.localeCompare(b.name_fr, 'fr'))
    : []

  return (
    <div className="space-y-5 rounded-[10px] border bg-surface p-4 sm:p-5">
      <PhotoPicker name={values.full_name} change={photo} onChange={onPhotoChange} />

      <Field id="full_name" label="Nom complet" error={errors.full_name}>
        <input
          {...describe('full_name', errors.full_name)}
          type="text"
          autoComplete="name"
          value={values.full_name}
          onChange={(event) => change({ full_name: event.target.value })}
          className={inputClass}
        />
      </Field>

      <Field id="phone" label="Téléphone" hint="Exemple : 22 123 456" error={errors.phone}>
        <input
          {...describe('phone', errors.phone, true)}
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          value={values.phone}
          onChange={(event) => change({ phone: event.target.value })}
          className={inputClass}
        />
      </Field>

      <Field id="governorate_code" label="Gouvernorat" error={errors.governorate_code}>
        <Select
          {...describe('governorate_code', errors.governorate_code)}
          value={values.governorate_code}
          disabled={governorates === 'loading'}
          onChange={(event) => change({ governorate_code: event.target.value })}
        >
          <option value="">{governorates === 'loading' ? 'Chargement…' : 'Choisir…'}</option>
          {sortedGovernorates.map((governorate) => (
            <option key={governorate.code} value={governorate.code}>
              {governorate.name_fr}
            </option>
          ))}
        </Select>
        {governorates === 'error' && (
          <div className="flex flex-wrap items-center gap-2 text-[14px] text-danger">
            <span>Impossible de charger la liste.</span>
            <Button type="button" variant="outline" onClick={retryGovernorates}>
              Réessayer
            </Button>
          </div>
        )}
      </Field>

      <Field id="education_level" label="Niveau d'études" optional error={errors.education_level}>
        <Select
          {...describe('education_level', errors.education_level)}
          value={values.education_level}
          onChange={(event) => change({ education_level: event.target.value })}
        >
          <option value="">Choisir…</option>
          {Object.entries(EDUCATION_LEVELS).map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </Select>
      </Field>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 2: Compétences
// ---------------------------------------------------------------------------

const SKILL_LEVEL_OPTIONS = [1, 2, 3, 4].map((level) => ({ value: level, label: SKILL_LEVELS[level] }))

export function StepSkills({ values, errors, change }: StepProps) {
  const { skills } = values

  return (
    <Section hint="Cherchez ce que vous savez faire, puis choisissez votre niveau.">
      <ReferenceSearch
        id="skill-search"
        label="Chercher une compétence"
        placeholder="Ex. : soudure, Excel, cuisine"
        search={searchSkills}
        itemLabel={(skill) => skill.label_fr}
        isAdded={(code) => skills.some((skill) => skill.code === code)}
        disabled={skills.length >= MAX_SKILLS}
        onAdd={(skill) =>
          change({
            skills: [
              { code: skill.code, label_fr: skill.label_fr, level: 2, source: 'self_declared', confidence: null },
              ...skills,
            ],
          })
        }
      />
      <FieldError id="skills" error={errors.skills} />

      {skills.length === 0 ? (
        <EmptyNote>Aucune compétence pour l'instant.</EmptyNote>
      ) : (
        <div className="space-y-3">
          <h4 className="font-medium text-ink">Vos compétences ({skills.length})</h4>
          <ul className="space-y-3">
            {skills.map((skill, index) => {
              const error =
                errors[`skills.${index}.code`] ?? errors[`skills.${index}.level`] ?? errors[`skills.${index}`]
              return (
                <li key={skill.code} className="space-y-3 rounded-[10px] border border-line p-3.5">
                  <div className="flex items-start justify-between gap-3">
                    <p className="pt-2.5 font-medium text-ink">{skill.label_fr}</p>
                    <RemoveButton
                      what={skill.label_fr}
                      onClick={() => change({ skills: skills.filter((item) => item.code !== skill.code) })}
                    />
                  </div>
                  <ChoiceButtons
                    label={`Votre niveau en ${skill.label_fr}`}
                    options={SKILL_LEVEL_OPTIONS}
                    value={skill.level}
                    onChange={(level) =>
                      change({ skills: skills.map((item) => (item.code === skill.code ? { ...item, level } : item)) })
                    }
                    className="grid-cols-2 sm:grid-cols-4"
                  />
                  <FieldError id={`skills-${index}`} error={error} />
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </Section>
  )
}

// ---------------------------------------------------------------------------
// Step 3: Expérience et préférences
// ---------------------------------------------------------------------------

const PERIOD_OPTIONS: { value: ExperienceValue['mode']; label: string }[] = [
  { value: 'dates', label: 'Dates' },
  { value: 'duration', label: 'Durée en mois' },
]

function ExperienceRow({
  experience,
  index,
  errors,
  onChange,
  onRemove,
}: {
  experience: ExperienceValue
  index: number
  errors: FormErrors
  onChange: (patch: Partial<ExperienceValue>) => void
  onRemove: () => void
}) {
  const at = `experiences.${index}`
  const id = (field: string) => `experience-${experience.key}-${field}`
  const titleError = errors[`${at}.job_title_raw`]
  const startError = errors[`${at}.start_date`]
  const endError = errors[`${at}.end_date`] ?? errors[at]
  const durationError = errors[`${at}.duration_months`]
  const name = experience.job_title_raw.trim() || `l'expérience ${index + 1}`

  return (
    <li className="space-y-4 rounded-[10px] border border-line p-3.5">
      <div className="flex items-center justify-between gap-3">
        <h4 className="font-medium text-ink">Expérience {index + 1}</h4>
        <RemoveButton what={name} onClick={onRemove} />
      </div>

      <Field id={id('title')} label="Poste" error={titleError}>
        <input
          {...describe(id('title'), titleError)}
          type="text"
          placeholder="Ex. : vendeur, soudeur, serveuse"
          value={experience.job_title_raw}
          onChange={(event) => onChange({ job_title_raw: event.target.value })}
          className={inputClass}
        />
      </Field>

      <Field id={id('employer')} label="Employeur" optional>
        <input
          id={id('employer')}
          type="text"
          value={experience.employer_name}
          onChange={(event) => onChange({ employer_name: event.target.value })}
          className={inputClass}
        />
      </Field>

      <div className="space-y-2">
        <p className="text-[15px] font-medium text-ink">
          Période <span className="font-normal text-ink-secondary">(facultatif)</span>
        </p>
        <ChoiceButtons
          label={`Période de l'expérience ${index + 1}`}
          options={PERIOD_OPTIONS}
          value={experience.mode}
          onChange={(mode) => onChange({ mode })}
          className="grid-cols-2"
        />
      </div>

      {experience.mode === 'dates' ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id={id('start')} label="Date de début" error={startError}>
            <input
              {...describe(id('start'), startError)}
              type="date"
              value={experience.start_date}
              onChange={(event) => onChange({ start_date: event.target.value })}
              className={inputClass}
            />
          </Field>
          <Field id={id('end')} label="Date de fin" hint="Vide si vous y travaillez encore." error={endError}>
            <input
              {...describe(id('end'), endError, true)}
              type="date"
              value={experience.end_date}
              onChange={(event) => onChange({ end_date: event.target.value })}
              className={inputClass}
            />
          </Field>
        </div>
      ) : (
        <Field id={id('duration')} label="Durée en mois" hint="Ex. : 18 pour un an et demi." error={durationError}>
          <input
            {...describe(id('duration'), durationError, true)}
            type="text"
            inputMode="numeric"
            value={experience.duration_months}
            onChange={(event) => onChange({ duration_months: event.target.value })}
            className={cn(inputClass, 'sm:max-w-40')}
          />
        </Field>
      )}
    </li>
  )
}

export function StepExperience({ values, errors, change }: StepProps) {
  const { experiences, desired_occupations: occupations, languages } = values

  function updateExperience(key: string, patch: Partial<ExperienceValue>) {
    change({ experiences: experiences.map((item) => (item.key === key ? { ...item, ...patch } : item)) })
  }

  return (
    <div className="space-y-5">
      <Section title="Expériences" hint="Vos emplois, stages ou petits travaux.">
        {experiences.length === 0 ? (
          <EmptyNote>Pas encore d'expérience ? Ce n'est pas grave, vous pouvez continuer.</EmptyNote>
        ) : (
          <ul className="space-y-3">
            {experiences.map((experience, index) => (
              <ExperienceRow
                key={experience.key}
                experience={experience}
                index={index}
                errors={errors}
                onChange={(patch) => updateExperience(experience.key, patch)}
                onRemove={() => change({ experiences: experiences.filter((item) => item.key !== experience.key) })}
              />
            ))}
          </ul>
        )}
        <Button
          type="button"
          variant="outline"
          className="w-full sm:w-auto"
          onClick={() => change({ experiences: [...experiences, newExperience()] })}
        >
          <Plus aria-hidden />
          Ajouter une expérience
        </Button>
      </Section>

      <Section title="Métiers souhaités" hint={`Les métiers que vous cherchez (${MAX_OCCUPATIONS} au maximum).`}>
        <ReferenceSearch
          id="occupation-search"
          label="Chercher un métier"
          placeholder="Ex. : électricien, cuisinier"
          search={searchOccupations}
          itemLabel={(occupation) => occupation.title_fr}
          isAdded={(code) => occupations.some((occupation) => occupation.code === code)}
          disabled={occupations.length >= MAX_OCCUPATIONS}
          onAdd={(occupation) =>
            change({
              desired_occupations: [...occupations, { code: occupation.code, title_fr: occupation.title_fr }],
            })
          }
        />
        <FieldError id="desired_occupations" error={errors.desired_occupations} />
        {occupations.length === 0 ? (
          <EmptyNote>Aucun métier choisi.</EmptyNote>
        ) : (
          <ul className="divide-y divide-line rounded-[10px] border border-line">
            {occupations.map((occupation, index) => (
              <li key={occupation.code} className="space-y-1 py-1 pr-1 pl-3.5">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium text-ink">{occupation.title_fr}</span>
                  <RemoveButton
                    what={occupation.title_fr}
                    onClick={() =>
                      change({ desired_occupations: occupations.filter((item) => item.code !== occupation.code) })
                    }
                  />
                </div>
                <FieldError
                  id={`desired_occupations-${index}`}
                  error={errors[`desired_occupations.${index}.code`] ?? errors[`desired_occupations.${index}`]}
                />
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Disponibilité">
        <Field
          id="available_from"
          label="Disponible à partir du"
          optional
          hint="Laissez vide si vous êtes disponible tout de suite."
          error={errors.available_from}
        >
          <input
            {...describe('available_from', errors.available_from, true)}
            type="date"
            value={values.available_from}
            onChange={(event) => change({ available_from: event.target.value })}
            className={cn(inputClass, 'sm:max-w-60')}
          />
        </Field>
      </Section>

      <Section title="Langues" hint="Les langues que vous parlez.">
        {languages.length === 0 ? (
          <EmptyNote>Aucune langue ajoutée.</EmptyNote>
        ) : (
          <ul className="space-y-3">
            {languages.map((language, index) => {
              const codeId = `language-${language.key}-code`
              const levelId = `language-${language.key}-level`
              const codeError = errors[`languages.${index}.code`] ?? errors[`languages.${index}`]
              const name = LANGUAGES[language.code] ?? (language.code.toUpperCase() || `la langue ${index + 1}`)
              const updateLanguage = (patch: Partial<typeof language>) =>
                change({
                  languages: languages.map((item) => (item.key === language.key ? { ...item, ...patch } : item)),
                })
              return (
                <li key={language.key} className="rounded-[10px] border border-line p-3.5">
                  <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
                    <Field id={codeId} label="Langue" error={codeError}>
                      <Select
                        {...describe(codeId, codeError)}
                        value={language.code}
                        onChange={(event) => updateLanguage({ code: event.target.value })}
                      >
                        <option value="">Choisir…</option>
                        {Object.entries(LANGUAGES).map(([code, label]) => (
                          <option key={code} value={code}>
                            {label}
                          </option>
                        ))}
                        {language.code && !LANGUAGES[language.code] && (
                          <option value={language.code}>{language.code.toUpperCase()}</option>
                        )}
                      </Select>
                    </Field>
                    <Field id={levelId} label="Niveau" error={errors[`languages.${index}.level`]}>
                      <Select
                        {...describe(levelId, errors[`languages.${index}.level`])}
                        value={language.level}
                        onChange={(event) => updateLanguage({ level: event.target.value })}
                      >
                        {Object.entries(LANGUAGE_LEVELS).map(([code, label]) => (
                          <option key={code} value={code}>
                            {label}
                          </option>
                        ))}
                      </Select>
                    </Field>
                    <div className="flex justify-end">
                      <RemoveButton
                        what={name}
                        onClick={() => change({ languages: languages.filter((item) => item.key !== language.key) })}
                      />
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
        <Button
          type="button"
          variant="outline"
          className="w-full sm:w-auto"
          onClick={() => change({ languages: [...languages, newLanguage()] })}
        >
          <Plus aria-hidden />
          Ajouter une langue
        </Button>
      </Section>

      <Section title="À propos de moi">
        <Field
          id="summary"
          label="Quelques mots sur vous"
          optional
          hint="Ce que vous savez faire, ce que vous aimez, ce que vous cherchez."
          error={errors.summary}
        >
          <textarea
            {...describe('summary', errors.summary, true)}
            rows={4}
            value={values.summary}
            onChange={(event) => change({ summary: event.target.value })}
            className={cn(inputClass, 'h-auto min-h-28 py-3 leading-relaxed')}
          />
          <p
            className={cn(
              'text-right text-[13px]',
              values.summary.trim().length > SUMMARY_MAX ? 'text-danger' : 'text-ink-secondary',
            )}
          >
            {values.summary.trim().length} / {SUMMARY_MAX}
          </p>
        </Field>
      </Section>

      <div className="space-y-2">
        <label
          htmlFor="consent"
          className={cn(
            'flex cursor-pointer items-start gap-3 rounded-[10px] border bg-surface p-4',
            errors.consent ? 'border-danger' : 'border-line',
          )}
        >
          <input
            {...describe('consent', errors.consent)}
            type="checkbox"
            checked={values.consent}
            onChange={(event) => change({ consent: event.target.checked })}
            className="mt-0.5 size-6 shrink-0 accent-teal"
          />
          <span className="space-y-1 text-[15px] text-ink">
            <span className="block">
              J'accepte que Mahara enregistre mon profil et le montre aux employeurs inscrits sur Mahara pour me
              proposer du travail : mon nom, ma photo, mon téléphone, mon e-mail, mon gouvernorat, mes
              compétences, mes expériences, mes études et mes langues.
            </span>
            <span className="block text-[14px] text-ink-secondary">
              Vous pouvez modifier votre profil à tout moment.
            </span>
          </span>
        </label>
        <FieldError id="consent" error={errors.consent} />
      </div>
    </div>
  )
}
