import { ArrowLeft, ArrowRight, CircleAlert, Save } from 'lucide-react'
import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { ApiError, deletePhoto, getGovernorates, saveProfile, uploadPhoto, type Profile } from '@/lib/api'
import { setCustomPhoto } from '@/lib/photo'
import {
  STEPS,
  normalizeValues,
  serverErrors,
  stepOfError,
  toProfileIn,
  validateStep,
  type FormErrors,
  type ProfileFormStart,
  type ProfileFormValues,
} from './form-values'
import type { PhotoChange } from './PhotoPicker'
import { StepIndicator } from './StepIndicator'
import { StepExperience, StepInfos, StepSkills, type GovernorateList } from './steps'

const LAST_STEP = STEPS.length - 1

/**
 * The 3-step profile form. Used to create and to edit a profile; `initialValues` prefills it
 * (the saved profile, or later a CV draft with `fromCv`). Saves with PUT /me/profile.
 */
export function ProfileForm({
  initialValues,
  fromCv = false,
  cancelTo = '/profil',
  onSaved,
}: {
  initialValues?: ProfileFormStart
  fromCv?: boolean
  cancelTo?: string
  /** photoFailed: the profile was saved but the new photo (or its removal) wasn't. */
  onSaved: (profile: Profile, result: { photoFailed: boolean }) => void
}) {
  const [values, setValues] = useState<ProfileFormValues>(() => normalizeValues(initialValues))
  const [step, setStep] = useState(0)
  // A step shows its errors (updated live) once the candidate has tried to leave it.
  const [checked, setChecked] = useState<boolean[]>(() => STEPS.map(() => false))
  const [fromServer, setFromServer] = useState<FormErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [governorates, setGovernorates] = useState<GovernorateList>('loading')
  const [focusRequest, setFocusRequest] = useState(0)
  // The photo is sent after the profile (a new profile must exist first), when "Enregistrer" is pressed.
  const [photo, setPhoto] = useState<PhotoChange>({ kind: 'keep' })
  const preview = photo.kind === 'upload' ? photo.preview : null
  useEffect(() => (preview ? () => URL.revokeObjectURL(preview) : undefined), [preview])

  const formRef = useRef<HTMLFormElement>(null)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const shownStep = useRef(step)

  const loadGovernorates = useCallback(() => {
    let ignore = false
    getGovernorates()
      .then((list) => {
        if (!ignore) setGovernorates(list)
      })
      .catch(() => {
        if (!ignore) setGovernorates('error')
      })
    return () => {
      ignore = true
    }
  }, [])

  useEffect(loadGovernorates, [loadGovernorates])

  // New step: back to the top, and move focus to its title for screen readers.
  useEffect(() => {
    if (shownStep.current === step) return
    shownStep.current = step
    window.scrollTo({ top: 0 })
    headingRef.current?.focus({ preventScroll: true })
  }, [step])

  // After a failed check: focus the first field in error (or scroll to the first message).
  useEffect(() => {
    if (focusRequest === 0) return
    const target = formRef.current?.querySelector<HTMLElement>('[aria-invalid="true"], [data-field-error]')
    if (!target) return
    if (target.matches('input, select, textarea')) {
      target.focus({ preventScroll: true })
    }
    target.scrollIntoView({ block: 'center' })
  }, [focusRequest])

  const errors: FormErrors = {
    ...(checked[step] ? validateStep(step, values) : {}),
    ...fromServer,
  }

  function change(patch: Partial<ProfileFormValues>) {
    setValues((current) => ({ ...current, ...patch }))
    // A server error goes away once the candidate edits that part of the form.
    const edited = Object.keys(patch)
    setFromServer((current) =>
      Object.fromEntries(Object.entries(current).filter(([path]) => !edited.includes(path.split('.')[0]))),
    )
    setFormError(null)
  }

  function markChecked(steps: number[]) {
    setChecked((current) => current.map((value, index) => value || steps.includes(index)))
  }

  /** Checks steps from..to-1; on the first one with errors, shows it and returns false. */
  function passes(from: number, to: number): boolean {
    for (let index = from; index < to; index += 1) {
      if (Object.keys(validateStep(index, values)).length > 0) {
        markChecked([index])
        setStep(index)
        setFocusRequest((n) => n + 1)
        return false
      }
    }
    return true
  }

  function goTo(target: number) {
    if (target > step && !passes(step, target)) return
    if (target > step) markChecked([step])
    setStep(target)
  }

  async function save() {
    markChecked([LAST_STEP])
    if (!passes(0, STEPS.length)) return
    setSaving(true)
    setFormError(null)
    try {
      const profile = await saveProfile(toProfileIn(values, fromCv))
      let photoFailed = false
      if (photo.kind !== 'keep') {
        try {
          if (photo.kind === 'upload') await uploadPhoto(photo.photo)
          else await deletePhoto()
          setCustomPhoto(photo.kind === 'upload' ? photo.photo : null)
          profile.has_photo = photo.kind === 'upload'
        } catch {
          photoFailed = true
        }
      }
      onSaved(profile, { photoFailed })
    } catch (error) {
      const fieldErrors = error instanceof ApiError && error.status === 422 ? serverErrors(error.detail) : null
      if (fieldErrors) {
        setFromServer(fieldErrors)
        setStep(Math.min(...Object.keys(fieldErrors).map(stepOfError)))
        setFocusRequest((n) => n + 1)
        setFormError("Certaines informations n'ont pas été acceptées. Vérifiez les messages en rouge.")
      } else if (error instanceof ApiError && error.status === 409) {
        setFormError('Votre profil a changé entre-temps. Appuyez de nouveau sur « Enregistrer ».')
      } else {
        setFormError("L'enregistrement a échoué. Vérifiez votre connexion et réessayez.")
      }
    } finally {
      setSaving(false)
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (saving) return
    if (step < LAST_STEP) goTo(step + 1)
    else void save()
  }

  const stepProps = { values, errors, change }

  return (
    <form ref={formRef} noValidate onSubmit={submit} className="mx-auto max-w-2xl space-y-5">
      <StepIndicator step={step} onGo={goTo} />

      <h2 ref={headingRef} tabIndex={-1} className="text-xl text-ink outline-none">
        {STEPS[step].title}
      </h2>

      {step === 0 && (
        <StepInfos
          {...stepProps}
          governorates={governorates}
          retryGovernorates={() => {
            setGovernorates('loading')
            loadGovernorates()
          }}
          photo={photo}
          onPhotoChange={setPhoto}
        />
      )}
      {step === 1 && <StepSkills {...stepProps} />}
      {step === 2 && <StepExperience {...stepProps} />}

      {/* Always visible at the bottom of the screen while the form is on screen. */}
      <div className="sticky bottom-0 z-20 -mx-4 -mb-6 border-t bg-surface/95 px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur lg:mx-0 lg:-mb-8 lg:bg-background/95 lg:px-0">
        {(formError || fromServer._form) && (
          <p role="alert" className="mb-3 flex items-start gap-1.5 text-[14px] text-danger">
            <CircleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
            {formError ?? fromServer._form}
          </p>
        )}
        <div className="grid grid-cols-2 gap-3">
          {step === 0 ? (
            <Button asChild variant="outline" size="lg">
              <Link to={cancelTo}>
                <ArrowLeft aria-hidden />
                Annuler
              </Link>
            </Button>
          ) : (
            <Button type="button" variant="outline" size="lg" onClick={() => goTo(step - 1)}>
              <ArrowLeft aria-hidden />
              Précédent
            </Button>
          )}
          {step < LAST_STEP ? (
            <Button type="submit" size="lg">
              Suivant
              <ArrowRight aria-hidden />
            </Button>
          ) : (
            <Button type="submit" variant="gold" size="lg" disabled={saving}>
              <Save aria-hidden />
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </Button>
          )}
        </div>
      </div>
    </form>
  )
}
