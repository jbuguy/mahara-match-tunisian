import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router'
import { Menu } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import { Logo } from './Logo'
import { NAV_ITEMS } from './nav'
import { SidebarUser, TopBarUserMenu } from './UserBits'

/** Nav links on teal. Active: light fill + 3px gold right border. */
function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav aria-label="Navigation principale" className="flex flex-col gap-1 py-2">
      {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex min-h-12 items-center gap-3 border-r-[3px] px-5 text-[15px] font-medium text-white/85 transition-colors hover:bg-white/10 hover:text-white',
              isActive ? 'border-gold bg-white/15 text-white' : 'border-transparent',
            )
          }
        >
          <Icon aria-hidden className="size-5 shrink-0" />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}

export function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { pathname } = useLocation()
  const current = NAV_ITEMS.find((item) => (item.to === '/' ? pathname === '/' : pathname.startsWith(item.to)))

  return (
    <div className="min-h-dvh bg-background">
      {/* 1024px and up: fixed 240px teal sidebar */}
      <aside className="fixed inset-y-0 left-0 hidden w-60 flex-col bg-teal lg:flex">
        <div className="flex h-18 items-center px-5">
          <Logo inverted />
        </div>
        <NavLinks />
        <SidebarUser />
      </aside>

      <div className="lg:pl-60">
        {/* Below 1024px: 56px top bar with logo and hamburger */}
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b bg-surface px-4 lg:hidden">
          <Logo />
          <Button
            variant="ghost"
            size="icon"
            aria-label="Ouvrir le menu"
            onClick={() => setDrawerOpen(true)}
          >
            <Menu />
          </Button>
        </header>

        {/* 1024px and up: 72px top bar */}
        <header className="sticky top-0 z-30 hidden h-18 items-center justify-between border-b bg-surface px-8 lg:flex">
          <span className="font-heading text-lg font-semibold text-ink">{current?.label ?? 'Mahara'}</span>
          <TopBarUserMenu />
        </header>

        <main className="mx-auto w-full max-w-5xl px-4 py-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>

      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent side="left" className="max-w-[85vw] gap-0 border-none bg-teal p-0 text-white data-[side=left]:w-[300px] [&>[data-slot=sheet-close]]:text-white [&>[data-slot=sheet-close]:hover]:bg-white/10 [&>[data-slot=sheet-close]:hover]:text-white">
          <div className="flex h-14 items-center px-5">
            <Logo inverted />
          </div>
          <SheetTitle className="sr-only">Menu</SheetTitle>
          <SheetDescription className="sr-only">Pages de l'espace candidat</SheetDescription>
          <NavLinks onNavigate={() => setDrawerOpen(false)} />
          <SidebarUser />
        </SheetContent>
      </Sheet>
    </div>
  )
}
