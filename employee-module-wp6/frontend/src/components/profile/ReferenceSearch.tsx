import { Check, Plus, Search } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { inputClass } from './field-attrs'

type Item = { code: string }

type Results<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'done'; query: string; items: T[] }

/**
 * Search box over a /reference endpoint. Results are a list of big buttons under the box;
 * choosing one calls onAdd and clears the box.
 */
export function ReferenceSearch<T extends Item>({
  id,
  label,
  placeholder,
  search,
  itemLabel,
  isAdded,
  onAdd,
  disabled,
}: {
  id: string
  label: string
  placeholder: string
  search: (q: string) => Promise<T[]>
  itemLabel: (item: T) => string
  isAdded: (code: string) => boolean
  onAdd: (item: T) => void
  disabled?: boolean
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Results<T>>({ status: 'idle' })
  const inputRef = useRef<HTMLInputElement>(null)
  const q = query.trim()

  useEffect(() => {
    if (!q) return
    let ignore = false
    const timer = setTimeout(() => {
      setResults({ status: 'loading' })
      search(q)
        .then((items) => {
          if (!ignore) setResults({ status: 'done', query: q, items })
        })
        .catch(() => {
          if (!ignore) setResults({ status: 'error' })
        })
    }, 250)
    return () => {
      ignore = true
      clearTimeout(timer)
    }
  }, [q, search])

  function choose(item: T) {
    onAdd(item)
    setQuery('')
    setResults({ status: 'idle' })
    inputRef.current?.focus()
  }

  const shown = q ? results : { status: 'idle' as const }

  return (
    <div className="space-y-2">
      <label htmlFor={id} className="block text-[15px] font-medium text-ink">
        {label}
      </label>
      <div className="relative">
        <Search
          aria-hidden
          className="pointer-events-none absolute top-1/2 left-3.5 size-5 -translate-y-1/2 text-ink-secondary"
        />
        <input
          ref={inputRef}
          id={id}
          type="search"
          autoComplete="off"
          enterKeyHint="search"
          placeholder={placeholder}
          value={query}
          disabled={disabled}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            // Enter must not submit the whole form.
            if (event.key === 'Enter') event.preventDefault()
          }}
          aria-describedby={`${id}-status`}
          className={`${inputClass} pl-11`}
        />
      </div>

      <p id={`${id}-status`} role="status" className="text-[14px] text-ink-secondary empty:hidden">
        {shown.status === 'loading' && 'Recherche…'}
        {shown.status === 'error' && <span className="text-danger">La recherche a échoué. Réessayez.</span>}
        {shown.status === 'done' && shown.items.length === 0 && `Aucun résultat pour « ${shown.query} ».`}
      </p>

      {shown.status === 'done' && shown.items.length > 0 && (
        <ul aria-label="Résultats" className="max-h-80 divide-y divide-line overflow-y-auto rounded-[10px] border">
          {shown.items.map((item) => {
            const added = isAdded(item.code)
            return (
              <li key={item.code}>
                <button
                  type="button"
                  disabled={added}
                  onClick={() => choose(item)}
                  className="flex min-h-12 w-full items-center gap-3 px-3.5 py-2 text-left text-[15px] text-ink transition-colors hover:bg-secondary focus-visible:bg-secondary focus-visible:outline-none disabled:text-ink-secondary"
                >
                  {added ? (
                    <Check aria-hidden className="size-5 shrink-0 text-teal" />
                  ) : (
                    <Plus aria-hidden className="size-5 shrink-0 text-teal" />
                  )}
                  <span className="flex-1">{itemLabel(item)}</span>
                  <span className="shrink-0 text-[14px] font-medium text-teal">{added ? 'Ajouté' : 'Ajouter'}</span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
