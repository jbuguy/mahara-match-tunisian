import { cn } from '@/lib/utils'
import { STEPS } from './form-values'

/** Three bars with the step names; each one can be tapped to go to that step. */
export function StepIndicator({ step, onGo }: { step: number; onGo: (step: number) => void }) {
  return (
    <nav aria-label="Étapes du formulaire" className="space-y-2">
      <p className="text-[14px] text-ink-secondary">
        Étape {step + 1} sur {STEPS.length}
      </p>
      <ol className="grid grid-cols-3 gap-2">
        {STEPS.map((item, index) => (
          <li key={item.short}>
            <button
              type="button"
              onClick={() => onGo(index)}
              aria-current={index === step ? 'step' : undefined}
              className="flex min-h-11 w-full flex-col gap-2 rounded-md pt-1 text-left outline-none focus-visible:ring-3 focus-visible:ring-teal/30"
            >
              <span className={cn('h-1.5 w-full rounded-full', index <= step ? 'bg-teal' : 'bg-line')} />
              <span
                className={cn(
                  'text-[13px] leading-tight sm:text-[14px]',
                  index === step ? 'font-semibold text-teal' : 'text-ink-secondary',
                )}
              >
                {index + 1}. {item.short}
              </span>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  )
}
