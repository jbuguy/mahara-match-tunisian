import { ArrowLeft, ArrowRight, CircleAlert, Save } from 'lucide-react'
import { useCallback, useEffect, useImperativeHandle, useRef, useState, type FormEvent, type Ref } from 'react'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import {
  ApiError,
  deletePhoto,
  getGovernorates,
  saveProfile,
  uploadPhoto,
  type AssistantUpdates,
  type Profile,
} from '@/lib/api'
import { setCustomPhoto } from '@/lib/photo'
import { changedFields, mergeAssistantUpdates, stepOfChanges, stepOfField, type Change } from './assistant-updates'
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
const FLASH_MS = 2600 // how long a field the assistant filled stays highlighted
const SHOW_FILLED_MS = 1500 // a filled field stays in view this long before the form moves to the next question

/** What the profile assistant can do with the form (through `ref`). */
export type ProfileFormHandle = {
  /** The values as they are now. */
  getValues: () => ProfileFormValues
  /**
   * Merges the assistant's updates and highlights them, then shows the step of the field its reply asks
   * about (`asking`). Returns what changed.
   */
  applyUpdates: (updates: AssistantUpdates, asking: string | null) => Change[]
  /** Scrolls to the top of the form and moves focus to the step title. */
  focusForm: () => void
}

/**
 * The 3-step profile form. Used to create and to edit a profile; `initialValues` prefills it
 * (the saved profile, or a CV draft with `fromCv`). Saves with PUT /me/profile.
 * The profile assistant fills it through `ref`; it never saves or ticks consent.
 */
export function ProfileForm({
  ref,
  initialValues,
  fromCv = false,
  cancelTo = '/profil',
  onSaved,
}: {
  ref?: Ref<ProfileFormHandle>
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
  // Fields the assistant just filled (highlighted for a moment), and whether it changed the step:
  // then the step change must not take focus away from the chat.
  const [flash, setFlash] = useState<ReadonlySet<Change>>(() => new Set())
  const quietStepChange = useRef(false)
  const nextStepTimer = useRef<number | undefined>(undefined) // the assistant's move to the asked step
  useEffect(() => () => window.clearTimeout(nextStepTimer.current), [])
  const valuesRef = useRef(values)
  useEffect(() => {
    valuesRef.current = values
  }, [values])

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

  // New step: back to the top, and move focus to its title for screen readers
  // (unless the assistant changed it: the candidate is typing in the chat).
  useEffect(() => {
    if (shownStep.current === step) return
    shownStep.current = step
    if (quietStepChange.current) {
      quietStepChange.current = false
      // Bring the new step's top into view if the page was scrolled past it; focus stays in the chat.
      if ((formRef.current?.getBoundingClientRect().top ?? 0) < 0) {
        formRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' })
      }
      return
    }
    window.scrollTo({ top: 0 })
    headingRef.current?.focus({ preventScroll: true })
  }, [step])

  // Fields the assistant filled: bring the first one into view, then stop highlighting after a moment.
  useEffect(() => {
    if (flash.size === 0) return
    formRef.current?.querySelector('[data-flash]')?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    const timer = window.setTimeout(() => setFlash(new Set()), FLASH_MS)
    return () => window.clearTimeout(timer)
  }, [flash])

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

  /** Shows another step for the assistant, without moving focus (the candidate is typing in the chat). */
  function showStepQuietly(target: number) {
    if (target === shownStep.current) return
    quietStepChange.current = true
    setStep(target)
  }

  /** The candidate moves through the form themselves: cancel the assistant's pending move. */
  function stopAssistantMoves() {
    window.clearTimeout(nextStepTimer.current)
    quietStepChange.current = false
  }

  useImperativeHandle(ref, () => ({
    getValues: () => valuesRef.current,
    applyUpdates(updates, asking) {
      window.clearTimeout(nextStepTimer.current)
      const merged = mergeAssistantUpdates(valuesRef.current, updates)
      const askedStep = asking ? stepOfField(asking) : null
      if (merged.changed.length === 0) {
        if (askedStep !== null) showStepQuietly(askedStep)
        return []
      }
      valuesRef.current = merged.values // a second reply before the next render builds on this one
      change(Object.fromEntries(changedFields(merged.changed).map((field) => [field, merged.values[field]])))
      setFlash(new Set(merged.changed))
      // Show what was filled first, then follow the question ("niveau d'études" filled → on to the skills).
      const filledStep = stepOfChanges(merged.changed)
      showStepQuietly(filledStep)
      if (askedStep !== null && askedStep !== filledStep) {
        nextStepTimer.current = window.setTimeout(() => showStepQuietly(askedStep), SHOW_FILLED_MS)
      }
      return merged.changed
    },
    focusForm() {
      formRef.current?.scrollIntoView({ block: 'start' })
      headingRef.current?.focus({ preventScroll: true })
    },
  }))

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
    stopAssistantMoves()
    if (target > step && !passes(step, target)) return
    if (target > step) markChecked([step])
    setStep(target)
  }

  async function save() {
    stopAssistantMoves()
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

  const stepProps = { values, errors, change, flash }

  return (
    <form ref={formRef} noValidate onSubmit={submit} className="mx-auto max-w-2xl scroll-mt-20 space-y-5 lg:scroll-mt-24">
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
