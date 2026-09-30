import { afterEach, describe, expect, it, vi } from 'vitest'
import { creerSession, envoyerReponse, getOffre, getQuestion, urlRecap } from './api.js'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('API onboarding', () => {
  it('creates a session and returns the exact response body', async () => {
    const payload = {
      session_id: 'session-1',
      question: { id: 'metier', texte: 'Quel métier ?', audio_url: '/audio/questions/metier' },
    }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(payload) })
    vi.stubGlobal('fetch', fetchMock)

    await expect(creerSession()).resolves.toEqual(payload)
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/sessions', { method: 'POST' })
  })

  it('reads the current question response', async () => {
    const payload = { termine: false, question: { id: 'date', texte: 'Date ?', audio_url: '/audio/questions/date' } }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(payload) }))

    await expect(getQuestion('session 1')).resolves.toEqual(payload)
    expect(fetch).toHaveBeenCalledWith('/api/v1/sessions/session%201/question', undefined)
  })

  it('sends the recording as multipart field audio', async () => {
    const payload = { texte_brut: 'نجار', valeur_extraite: 'نجار', question_suivante: null, termine: true }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(payload) })
    vi.stubGlobal('fetch', fetchMock)
    const blob = new Blob(['webm-data'], { type: 'audio/webm;codecs=opus' })

    await expect(envoyerReponse('session-1', blob)).resolves.toEqual(payload)
    const [, options] = fetchMock.mock.calls[0]
    expect(options.method).toBe('POST')
    expect(options.body.get('audio')).toBeInstanceOf(File)
    expect(options.body.get('audio').name).toBe('reponse.webm')
  })

  it('reads plain text offers and builds the recap URL', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, text: () => Promise.resolve('Offre de test') }))

    await expect(getOffre('session-1')).resolves.toBe('Offre de test')
    expect(urlRecap('session-1')).toBe('/api/v1/sessions/session-1/recap-audio')
  })

  it('exposes structured retryable transcription errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: () => Promise.resolve({
        detail: { code: 'transcription_vide', message: 'Aucune réponse reconnue.', reessayer: true },
      }),
    }))

    await expect(creerSession()).rejects.toMatchObject({
      message: 'Aucune réponse reconnue.',
      status: 422,
      code: 'transcription_vide',
      retryable: true,
    })
  })

  it('turns an unavailable API into a readable error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(creerSession()).rejects.toThrow("L'API est injoignable.")
  })
})