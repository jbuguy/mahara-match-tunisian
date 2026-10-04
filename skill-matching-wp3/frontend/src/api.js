const API_BASE = '/api'
let referenceDataPromise

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, options)
  } catch {
    throw new Error('Le serveur Mahara Match est injoignable. Vérifiez que le backend est démarré sur le port 8000.')
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    if ([502, 503, 504].includes(response.status)) {
      throw new Error('Le backend Mahara Match ne répond pas. Démarrez-le avec « python main.py » dans le dossier WP3.')
    }
    const detail = payload?.detail
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).join(', ')
      : detail || `Erreur du serveur (${response.status}).`
    const error = new Error(message)
    error.status = response.status
    throw error
  }
  return payload
}

export function parseCv(candidatId, governorateCode, file) {
  const formData = new FormData()
  formData.append('fichier', file)
  const params = new URLSearchParams({ candidat_id: candidatId })
  if (governorateCode) params.set('governorate_code', governorateCode)
  return request(`/v1/parse-cv?${params}`, { method: 'POST', body: formData })
}

export function getOffres() {
  return request('/v1/offres')
}

export function getSkills() {
  return request('/v1/skills')
}

export function getReferenceData() {
  if (!referenceDataPromise) {
    referenceDataPromise = Promise.all([getOffres(), getSkills()])
      .then(([offres, skills]) => ({ offres, skills }))
      .catch((error) => {
        referenceDataPromise = null
        throw error
      })
  }
  return referenceDataPromise
}

export function getMatches(candidatId) {
  const params = new URLSearchParams({ candidat_id: candidatId })
  return request(`/v1/match?${params}`, { method: 'POST' })
}

export function getRoadmap(candidatId, offreId) {
  return request(`/v1/roadmap/${encodeURIComponent(candidatId)}/${encodeURIComponent(offreId)}`)
}