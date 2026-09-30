const API_ROOT = '/api/v1/sessions'

async function request(url, options) {
  let response
  try {
    response = await fetch(url, options)
  } catch {
    throw new Error("L'API est injoignable. Vérifiez que le serveur est lancé puis réessayez.")
  }

  if (!response.ok) {
    let payload
    try {
      payload = await response.json()
    } catch {
      payload = null
    }

    const detail = payload?.detail
    const error = new Error(
      typeof detail === 'string'
        ? detail
        : detail?.message || `La requête a échoué (HTTP ${response.status}).`,
    )
    error.status = response.status
    error.code = detail?.code
    error.retryable = detail?.reessayer === true
    throw error
  }

  return response
}

export async function creerSession() {
  const response = await request(API_ROOT, { method: 'POST' })
  return response.json()
}

export async function getQuestion(sessionId) {
  const response = await request(`${API_ROOT}/${encodeURIComponent(sessionId)}/question`)
  return response.json()
}

export async function envoyerReponse(sessionId, blob) {
  const formData = new FormData()
  const mimeExtension = {
    aac: 'aac',
    mp4: 'm4a',
    mpeg: 'mp3',
    ogg: 'ogg',
    wav: 'wav',
    webm: 'webm',
    'x-wav': 'wav',
  }
  const mimeSubtype = blob.type.split(';')[0].split('/')[1]
  const fileExtension = blob.name?.split('.').pop()?.toLowerCase()
  const extension = mimeExtension[mimeSubtype] || mimeExtension[fileExtension] || 'webm'
  formData.append('audio', blob, `reponse.${extension}`)
  const response = await request(`${API_ROOT}/${encodeURIComponent(sessionId)}/reponse`, {
    method: 'POST',
    body: formData,
  })
  return response.json()
}

export async function getOffre(sessionId) {
  const response = await request(`${API_ROOT}/${encodeURIComponent(sessionId)}/offre`)
  return response.text()
}

export function urlRecap(sessionId) {
  return `${API_ROOT}/${encodeURIComponent(sessionId)}/recap-audio`
}