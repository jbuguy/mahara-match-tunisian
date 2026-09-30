import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router'

import './index.css'
import { AppShell } from '@/components/layout/AppShell'
import { AccueilPage } from '@/pages/AccueilPage'
import { LoginPage } from '@/pages/LoginPage'
import { CandidaturesPage, FormationPage, OffresPage, ProfilPage } from '@/pages/placeholders'

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <AppShell />,
    children: [
      { index: true, element: <AccueilPage /> },
      { path: 'offres', element: <OffresPage /> },
      { path: 'candidatures', element: <CandidaturesPage /> },
      { path: 'formation', element: <FormationPage /> },
      { path: 'profil', element: <ProfilPage /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
