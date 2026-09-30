import { ChevronDown, LogOut } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { displayName, initials, useAuth } from '@/lib/auth-context'
import { cn } from '@/lib/utils'

function Avatar({ name, inverted = false }: { name: string; inverted?: boolean }) {
  return (
    <span
      aria-hidden
      className={cn(
        'grid size-10 shrink-0 place-items-center rounded-full font-heading text-[15px] font-semibold',
        inverted ? 'bg-white text-teal' : 'bg-teal text-white',
      )}
    >
      {initials(name)}
    </span>
  )
}

/** Bottom of the teal sidebar and drawer: who is signed in + "Se déconnecter". */
export function SidebarUser() {
  const { session, signOut } = useAuth()
  const name = displayName(session)

  return (
    <div className="mt-auto space-y-3 border-t border-white/15 p-4">
      <div className="flex items-center gap-3">
        <Avatar name={name} inverted />
        <span className="truncate text-[15px] font-medium text-white">{name}</span>
      </div>
      <Button
        variant="ghost"
        className="w-full justify-start text-white/85 hover:bg-white/10 hover:text-white"
        onClick={signOut}
      >
        <LogOut aria-hidden className="size-5" />
        Se déconnecter
      </Button>
    </div>
  )
}

/** Right side of the 72px desktop top bar: initials + name, with a small menu. */
export function TopBarUserMenu() {
  const { session, signOut } = useAuth()
  const name = displayName(session)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="h-12 gap-3 px-2" aria-label={`Menu du compte de ${name}`}>
          <Avatar name={name} />
          <span className="max-w-48 truncate text-[15px] text-ink">{name}</span>
          <ChevronDown aria-hidden className="text-ink-secondary" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuItem className="min-h-11 gap-3 px-3 text-[15px]" onSelect={signOut}>
          <LogOut aria-hidden className="size-5" />
          Se déconnecter
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
