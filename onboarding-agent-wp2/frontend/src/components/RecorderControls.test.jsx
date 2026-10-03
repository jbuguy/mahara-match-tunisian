import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import RecorderControls from './RecorderControls.jsx'
import textes from '../textes.js'

let recorderInstance

class FakeMediaRecorder {
  static isTypeSupported = vi.fn((type) => type === 'audio/webm;codecs=opus')

  constructor(_stream, options) {
    this.mimeType = options?.mimeType || ''
    this.state = 'inactive'
    recorderInstance = this
  }

  start() {
    this.state = 'recording'
  }

  stop() {
    this.state = 'inactive'
    this.onstop?.()
  }
}

const track = { stop: vi.fn() }
const stream = { getTracks: () => [track] }

beforeEach(() => {
  recorderInstance = null
  track.stop.mockClear()
  FakeMediaRecorder.isTypeSupported.mockClear()
  FakeMediaRecorder.isTypeSupported.mockImplementation((type) => type === 'audio/webm;codecs=opus')
  vi.stubGlobal('MediaRecorder', FakeMediaRecorder)
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia: vi.fn().mockResolvedValue(stream) },
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('RecorderControls', () => {
  it('uses WebM/Opus and sends a sufficiently long recording', async () => {
    const onRecorded = vi.fn()
    let now = 1000
    vi.spyOn(Date, 'now').mockImplementation(() => now)
    render(<RecorderControls onRecorded={onRecorded} />)

    fireEvent.click(screen.getByRole('button', { name: textes.enregistrer }))
    await waitFor(() => expect(recorderInstance).not.toBeNull())
    expect(recorderInstance.mimeType).toBe('audio/webm;codecs=opus')
    recorderInstance.ondataavailable({ data: new Blob(['speech'], { type: 'audio/webm' }) })
    now = 2000
    fireEvent.click(screen.getByRole('button', { name: textes.arreter }))

    expect(onRecorded).toHaveBeenCalledOnce()
    expect(onRecorded.mock.calls[0][0].type).toBe('audio/webm;codecs=opus')
    expect(track.stop).toHaveBeenCalledOnce()
  })

  it('rejects recordings that are too short', async () => {
    const onRecorded = vi.fn()
    let now = 1000
    vi.spyOn(Date, 'now').mockImplementation(() => now)
    render(<RecorderControls onRecorded={onRecorded} />)

    fireEvent.click(screen.getByRole('button', { name: textes.enregistrer }))
    await waitFor(() => expect(recorderInstance).not.toBeNull())
    recorderInstance.ondataavailable({ data: new Blob(['x']) })
    now = 1300
    fireEvent.click(screen.getByRole('button', { name: textes.arreter }))

    expect(await screen.findByRole('alert')).toHaveTextContent(textes.erreurs.enregistrementCourt)
    expect(onRecorded).not.toHaveBeenCalled()
  })

  it('explains when microphone permission is denied', async () => {
    navigator.mediaDevices.getUserMedia.mockRejectedValueOnce(new DOMException('Denied', 'NotAllowedError'))
    render(<RecorderControls onRecorded={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: textes.enregistrer }))

    expect(await screen.findByRole('alert')).toHaveTextContent(textes.erreurs.microphoneRefuse)
  })
})