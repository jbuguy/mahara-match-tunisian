import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router'

import './index.css'
import { AuthProvider } from '@/components/auth/AuthProvider'
import { RequireAuth } from '@/components/auth/RequireAuth'
import { AppShell } from '@/components/layout/AppShell'
import { AccueilPage } from '@/pages/AccueilPage'
import { AuthCallbackPage } from '@/pages/AuthCallbackPage'
import { LoginPage } from '@/pages/LoginPage'
import {
  CandidaturesPage,
  CvImportPage,
  FormationPage,
  OffresPage,
  ProfilFormPage,
} from '@/pages/placeholders'
import { ProfilPage } from '@/pages/ProfilPage'

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/auth/callback', element: <AuthCallbackPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <AccueilPage /> },
          { path: 'offres', element: <OffresPage /> },
          { path: 'candidatures', element: <CandidaturesPage /> },
          { path: 'formation', element: <FormationPage /> },
          { path: 'profil', element: <ProfilPage /> },
          { path: 'profil/modifier', element: <ProfilFormPage /> },
          { path: 'profil/importer-cv', element: <CvImportPage /> },
        ],
      },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </StrictMode>,
)
