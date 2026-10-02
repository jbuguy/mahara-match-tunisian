import { createContext, useContext, useEffect, useState } from 'react'
import { getReferenceData } from '../api.js'

const CandidatContext = createContext(null)
const EMPTY_REFERENCE_DATA = { offres: [], skills: {} }

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
  const [referenceData, setReferenceData] = useState(EMPTY_REFERENCE_DATA)
  const [referenceLoading, setReferenceLoading] = useState(true)
  const [referenceError, setReferenceError] = useState('')

  useEffect(() => {
    let active = true
    getReferenceData()
      .then((data) => { if (active) setReferenceData(data) })
      .catch((error) => { if (active) setReferenceError(error.message) })
      .finally(() => { if (active) setReferenceLoading(false) })
    return () => { active = false }
  }, [])

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
    <CandidatContext.Provider value={{
      candidatId,
      setCandidatId: updateCandidatId,
      profil,
      setProfil: updateProfil,
      offres: referenceData.offres,
      skillLabels: referenceData.skills,
      referenceLoading,
      referenceError,
    }}>
      {children}
    </CandidatContext.Provider>
  )
}

export function useCandidat() {
  const context = useContext(CandidatContext)
  if (!context) throw new Error('useCandidat doit être utilisé dans CandidatProvider.')
  return context
}