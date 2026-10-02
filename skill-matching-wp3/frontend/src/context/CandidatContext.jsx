import { createContext, useContext, useState } from 'react'

const CandidatContext = createContext(null)

function readStoredProfile() {
  try {
    return JSON.parse(sessionStorage.getItem('mahara-candidat-profil') || 'null')
  } catch {
    return null
  }
}

export function CandidatProvider({ children }) {
  const [candidatId, setCandidatId] = useState(() => localStorage.getItem('mahara-candidat-id') || 'demo')
  const [profil, setProfil] = useState(readStoredProfile)

  function updateCandidatId(value) {
    if (value !== candidatId) {
      setProfil(null)
      sessionStorage.removeItem('mahara-candidat-profil')
    }
    setCandidatId(value)
    localStorage.setItem('mahara-candidat-id', value)
  }

  function updateProfil(value) {
    setProfil(value)
    if (value) sessionStorage.setItem('mahara-candidat-profil', JSON.stringify(value))
    else sessionStorage.removeItem('mahara-candidat-profil')
  }

  return (
    <CandidatContext.Provider value={{ candidatId, setCandidatId: updateCandidatId, profil, setProfil: updateProfil }}>
      {children}
    </CandidatContext.Provider>
  )
}

export function useCandidat() {
  const context = useContext(CandidatContext)
  if (!context) throw new Error('useCandidat doit être utilisé dans CandidatProvider.')
  return context
}