import { cn } from '@/lib/utils'

/** Teal "M" tile + "Mahara" wordmark. `inverted` is for the teal sidebar/drawer. */
export function Logo({ inverted = false }: { inverted?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <span
        aria-hidden
        className={cn(
          'grid size-9 place-items-center rounded-[10px] font-heading text-lg font-bold',
          inverted ? 'bg-white text-teal' : 'bg-teal text-white',
        )}
      >
        M
      </span>
      <span className={cn('font-heading text-xl font-bold', inverted ? 'text-white' : 'text-teal')}>
        Mahara
      </span>
    </span>
  )
}
