import { ChevronDown, CircleAlert } from 'lucide-react'
import type { ComponentProps, ReactNode } from 'react'

import { cn } from '@/lib/utils'
import { inputClass } from './field-attrs'

export function FieldError({ id, error }: { id: string; error?: string }) {
  if (!error) return null
  return (
    <p id={`${id}-error`} data-field-error className="flex items-start gap-1.5 text-[14px] text-danger">
      <CircleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
      {error}
    </p>
  )
}

export function Field({
  id,
  label,
  optional,
  hint,
  error,
  children,
  className,
}: {
  id: string
  label: string
  optional?: boolean
  hint?: string
  error?: string
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={id} className="block text-[15px] font-medium text-ink">
        {label}
        {optional && <span className="font-normal text-ink-secondary"> (facultatif)</span>}
      </label>
      {hint && (
        <p id={`${id}-hint`} className="text-[14px] text-ink-secondary">
          {hint}
        </p>
      )}
      {children}
      <FieldError id={id} error={error} />
    </div>
  )
}

export function Select({ className, children, ...props }: ComponentProps<'select'>) {
  return (
    <div className="relative">
      <select {...props} className={cn(inputClass, 'appearance-none pr-10', className)}>
        {children}
      </select>
      <ChevronDown
        aria-hidden
        className="pointer-events-none absolute top-1/2 right-3.5 size-5 -translate-y-1/2 text-ink-secondary"
      />
    </div>
  )
}

/** A block inside a step, with an optional title (left out when the step title already says it). */
export function Section({
  title,
  hint,
  children,
}: {
  title?: string
  hint?: string
  children: ReactNode
}) {
  return (
    <section className="space-y-4 rounded-[10px] border bg-surface p-4 sm:p-5">
      <div className="space-y-1">
        {title && <h3 className="text-lg text-ink">{title}</h3>}
        {hint && <p className="text-[14px] text-ink-secondary">{hint}</p>}
      </div>
      {children}
    </section>
  )
}
