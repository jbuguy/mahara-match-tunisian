import { Camera, RotateCcw } from 'lucide-react'
import { useState, type ChangeEvent } from 'react'

import { Avatar } from '@/components/Avatar'
import { Button } from '@/components/ui/button'
import { MAX_SOURCE_BYTES, squareJpeg } from '@/lib/image'
import { useUserPhoto } from '@/lib/photo'
import { FieldError } from './fields'

/** What "Enregistrer" will do with the photo. */
export type PhotoChange =
  | { kind: 'keep' }
  | { kind: 'upload'; photo: Blob; preview: string }
  | { kind: 'remove' }

/** Photo block of step 1: shows the photo that will be used, lets the candidate pick another or go back to Google's. */
export function PhotoPicker({
  name,
  change,
  onChange,
}: {
  name: string
  change: PhotoChange
  onChange: (change: PhotoChange) => void
}) {
  const { src, hasCustom, google } = useUserPhoto()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const shown = change.kind === 'upload' ? change.preview : change.kind === 'remove' ? google : src
  const custom = change.kind === 'upload' || (change.kind === 'keep' && hasCustom)

  async function pick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = '' // choosing the same file again still triggers a change
    if (!file) return
    if (file.size > MAX_SOURCE_BYTES) {
      setError('Cette photo est trop lourde (20 Mo au maximum).')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const photo = await squareJpeg(file)
      onChange({ kind: 'upload', photo, preview: URL.createObjectURL(photo) })
    } catch {
      setError('Impossible de lire cette photo. Choisissez une photo JPG ou PNG.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-4">
        <Avatar name={name || '?'} src={shown} className="size-24 text-3xl" />
        <div className="flex min-w-0 flex-1 flex-col items-start gap-2">
          <p className="text-[15px] font-medium text-ink">
            Photo <span className="font-normal text-ink-secondary">(facultatif)</span>
          </p>
          <Button asChild variant="outline" className="cursor-pointer focus-within:ring-3 focus-within:ring-teal/30">
            <label>
              <Camera aria-hidden />
              {busy ? 'Préparation…' : 'Changer la photo'}
              <input
                type="file"
                accept="image/*"
                className="sr-only"
                disabled={busy}
                onChange={pick}
                aria-describedby={error ? 'photo-error' : undefined}
              />
            </label>
          </Button>
          {custom && (
            <Button
              type="button"
              variant="ghost"
              className="h-auto min-h-11 px-3 py-2 text-left whitespace-normal text-ink-secondary"
              onClick={() => {
                setError(null)
                onChange({ kind: hasCustom ? 'remove' : 'keep' })
              }}
            >
              <RotateCcw aria-hidden />
              {google ? 'Utiliser la photo Google' : 'Retirer la photo'}
            </Button>
          )}
        </div>
      </div>
      <FieldError id="photo" error={error ?? undefined} />
    </div>
  )
}
