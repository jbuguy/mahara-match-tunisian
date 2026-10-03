/** 48px high, 16px text (no zoom on iOS), red border when aria-invalid. */
export const inputClass =
  'h-12 w-full min-w-0 rounded-[10px] border border-line bg-surface px-3.5 text-base text-ink outline-none transition-colors placeholder:text-ink-secondary/70 focus-visible:border-teal focus-visible:ring-3 focus-visible:ring-teal/20 disabled:opacity-60 aria-invalid:border-danger aria-invalid:ring-danger/20'

/** id, aria-invalid and aria-describedby for an input with an optional hint and error. */
export function describe(id: string, error?: string, hasHint = false) {
  const describedBy = [hasHint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ')
  return {
    id,
    'aria-invalid': error ? true : undefined,
    'aria-describedby': describedBy || undefined,
  }
}
