import { Logo } from '@/components/layout/Logo'
import { PageTitle } from './placeholders'

export function LoginPage() {
  return (
    <main className="grid min-h-dvh place-items-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6 rounded-[10px] border bg-surface p-8 text-center">
        <div className="flex justify-center">
          <Logo />
        </div>
        <PageTitle>Connexion</PageTitle>
        <p className="text-ink-secondary">La connexion avec Google arrive bientôt.</p>
      </div>
    </main>
  )
}
