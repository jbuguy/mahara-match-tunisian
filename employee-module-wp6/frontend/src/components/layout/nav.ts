import { Briefcase, FileText, GraduationCap, House, User, type LucideIcon } from 'lucide-react'

export type NavItem = { to: string; label: string; icon: LucideIcon }

export const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Accueil', icon: House },
  { to: '/offres', label: 'Offres', icon: Briefcase },
  { to: '/candidatures', label: 'Candidatures', icon: FileText },
  { to: '/formation', label: 'Formation', icon: GraduationCap },
  { to: '/profil', label: 'Profil', icon: User },
]
