import type { ReactNode } from 'react'
import { LoaderCircle } from 'lucide-react'

import { Logo } from '@/components/layout/Logo'

/** Centered logo + message, for the short waits before a page can show (session restore, Google redirect). */
export function FullPageMessage({ children, spinner = true }: { children: ReactNode; spinner?: boolean }) {
  return (
    <main className="grid min-h-dvh place-items-center bg-background px-4">
      <div role="status" className="flex flex-col items-center gap-5 text-center text-ink-secondary">
        <Logo />
        <div className="flex flex-col items-center gap-3">
          {spinner && <LoaderCircle aria-hidden className="size-6 animate-spin text-teal" />}
          {children}
        </div>
      </div>
    </main>
  )
}
