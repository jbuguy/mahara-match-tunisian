import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { deleteMockInterview, downloadMockInterviewReport, getMockInterview, getMockInterviews, getMyApplications, requestJson, reviewMockInterview, saveMockInterview, saveMockInterviewDraftAnswer, startMockInterview, submitMockInterviewAnswer, type CandidateApplication, type MockInterview } from '../lib/api'
import { useVoiceInput } from '../lib/useVoiceInput'

type Occupation = { code: string; title_fr: string }
type ExperienceMode = 'setup' | 'cockpit' | 'feedback'

const locale: Record<MockInterview['language'], string> = { fr: 'fr-FR', ar: 'ar', derja: 'ar-TN' }

function escapeHtml(text: string) {
  const entities: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }
  return text.replace(/[&<>"']/g, (char) => entities[char])
}

export function MockInterviewPage() {
  const voice = useVoiceInput('/api/v1/me/assistant/transcribe')
  const [occupations, setOccupations] = useState<Occupation[]>([])
  const [applications, setApplications] = useState<CandidateApplication[]>([])
  const [savedItems, setSavedItems] = useState<MockInterview[]>([])
  const [session, setSession] = useState<MockInterview | null>(null)
  const [mode, setMode] = useState<ExperienceMode>('setup')
  const [occupationCode, setOccupationCode] = useState('')
  const [targetOfferId, setTargetOfferId] = useState<string | null>(null)
  const [customTitle, setCustomTitle] = useState('')
  const [questionCount, setQuestionCount] = useState(5)
  const [language, setLanguage] = useState<MockInterview['language']>('fr')
  const [consent, setConsent] = useState(false)
  const [answer, setAnswer] = useState('')
  const [showExit, setShowExit] = useState(false)
  const [loading, setLoading] = useState(Boolean(localStorage.getItem('mahara_access_token')))
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    if (!localStorage.getItem('mahara_access_token')) { setLoading(false); return }
    let active = true
    Promise.allSettled([
      requestJson<Occupation[]>('/api/v1/reference/occupations'),
      getMockInterviews(),
      getMyApplications(),
    ]).then(([occupationResult, sessionResult, applicationResult]) => {
      if (!active) return
      if (occupationResult.status === 'fulfilled') setOccupations(occupationResult.value)
      else setError('Could not load the occupation list. You can still enter a custom job title.')
      if (sessionResult.status === 'fulfilled') setSavedItems(sessionResult.value.items)
      if (applicationResult.status === 'fulfilled') setApplications(applicationResult.value)
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  useEffect(() => { if (voice.transcript) setAnswer(voice.transcript) }, [voice.transcript])

  const selectedOccupation = useMemo(() => occupations.find((item) => item.code === occupationCode), [occupations, occupationCode])
  const currentQuestion = session?.questions[session.current_index]
  const targetTitle = selectedOccupation?.title_fr || customTitle.trim()

  async function begin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true); setError(''); setNotice('')
    try {
      const started = await startMockInterview({ target_title: targetTitle, occupation_code: selectedOccupation?.code ?? null, target_offer_id: targetOfferId, language, question_count: questionCount, consent })
      setSession(started); setAnswer(''); setMode('cockpit')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not start the practice interview.') }
    finally { setPending(false) }
  }

  async function resume(id: string) {
    setPending(true); setError('')
    try {
      const loaded = await getMockInterview(id)
      setSession(loaded); setAnswer(loaded.draft_answer ?? '')
      setMode(loaded.status === 'completed' ? 'feedback' : 'cockpit')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not reopen this practice session.') }
    finally { setPending(false) }
  }

  async function completeReview(id: string, current: MockInterview) {
    try {
      const reviewed = await reviewMockInterview(id)
      setSession(reviewed); setMode('feedback'); setError('')
    } catch (cause) {
      setSession(current); setMode('cockpit')
      setError(cause instanceof Error ? cause.message : 'The coaching service is unavailable. Your answers are saved; retry the review shortly.')
    }
  }

  async function submitAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!session || !answer.trim()) return
    setPending(true); setError(''); setNotice('')
    try {
      const updated = await submitMockInterviewAnswer(session.session_id, session.current_index, answer.trim())
      setSession(updated); setAnswer('')
      if (updated.current_index >= updated.question_count) await completeReview(session.session_id, updated)
      else setNotice('Response saved privately. Ready for the next question?')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save this response.') }
    finally { setPending(false) }
  }

  async function retryReview() {
    if (!session) return
    setPending(true); setError('')
    await completeReview(session.session_id, session)
    setPending(false)
  }

  async function saveForLater() {
    if (!session) return
    setPending(true); setError('')
    try {
      if (answer.trim() && session.status === 'in_progress') await saveMockInterviewDraftAnswer(session.session_id, answer)
      await saveMockInterview(session.session_id, true)
      const result = await getMockInterviews(); setSavedItems(result.items)
      setSession(null); setMode('setup'); setShowExit(false); setNotice('Saved in your private space for 30 days.')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save this session.') }
    finally { setPending(false) }
  }

  async function discardSession() {
    if (!session) return
    setPending(true); setError('')
    try {
      await deleteMockInterview(session.session_id)
      setSavedItems((items) => items.filter((item) => item.session_id !== session.session_id))
      setSession(null); setMode('setup'); setShowExit(false); setNotice('Session and responses permanently deleted.')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not delete this session.') }
    finally { setPending(false) }
  }

  async function deleteSavedSession(id: string) {
    if (!window.confirm('Delete this saved interview, its answers, and its coaching feedback permanently?')) return
    setPending(true); setError('')
    try {
      await deleteMockInterview(id)
      setSavedItems((items) => items.filter((item) => item.session_id !== id))
      setNotice('Saved practice session deleted.')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not delete this session.') }
    finally { setPending(false) }
  }

  async function downloadAdvice() {
    if (!session) return
    setPending(true); setError('')
    try {
      if (session.language !== 'fr' && session.feedback) {
        const printWindow = window.open('', '_blank')
        if (!printWindow) throw new Error('Allow the new window to print or download this advice sheet.')
        const direction = session.language === 'ar' ? 'rtl' : 'auto'
        const title = session.language === 'ar' ? 'إرشادات مقابلة العمل' : 'نصائح للتدرب على مقابلة العمل'
        const evidence = session.language === 'ar' ? 'الدليل' : 'ما نجح'
        const next = session.language === 'ar' ? 'الخطوة التالية' : 'جرّب في المرة القادمة'
        const answers = session.feedback.answers.map((item) => `<article><h3>${escapeHtml(session.questions[item.question_index]?.prompt ?? '')}</h3><p><b>${evidence}:</b> ${escapeHtml(item.strength)}</p><p><b>${next}:</b> ${escapeHtml(item.improvement)}</p><p><b>${session.language === 'ar' ? 'صياغة مقترحة' : 'صياغة مقترحة'}:</b> ${escapeHtml(item.example)}</p></article>`).join('')
        const topics = session.feedback.topics.map((item) => `<article><h3>${escapeHtml(item.status)} · ${escapeHtml(item.title)}</h3><p>${escapeHtml(item.evidence)}</p><p><b>${next}:</b> ${escapeHtml(item.next_step)}</p></article>`).join('')
        printWindow.document.write(`<!doctype html><html lang="${session.language === 'ar' ? 'ar' : 'ar-TN'}" dir="${direction}"><meta charset="utf-8"><title>${title}</title><style>body{font:16px/1.7 Arial,Tahoma,sans-serif;color:#221a14;max-width:820px;margin:40px auto;padding:0 24px}h1,h2{color:#00376f}article{border-top:1px solid #d5c7b2;padding:14px 0;break-inside:avoid}.notice{background:#edf5e7;padding:12px}@media print{button{display:none}body{margin:0 auto}}</style><h1>${title}</h1><p>${escapeHtml(session.target_title)} · ${session.question_count} ${session.language === 'ar' ? 'أسئلة' : 'أسئلة'}</p><p class="notice">${session.language === 'ar' ? 'تدريب فقط. لا توجد درجة أو نتيجة توظيف.' : 'تدريب فقط. لا توجد درجة أو نتيجة توظيف.'}</p><h2>${session.language === 'ar' ? 'ملخص' : 'ملخص'}</h2><p>${escapeHtml(session.feedback.overall_summary)}</p><h2>${session.language === 'ar' ? 'مجالات التدريب' : 'مجالات التدريب'}</h2>${topics}<h2>${session.language === 'ar' ? 'مراجعة الأجوبة' : 'مراجعة الأجوبة'}</h2>${answers}<button onclick="window.print()">${session.language === 'ar' ? 'طباعة أو حفظ PDF' : 'طباعة أو حفظ PDF'}</button><script>window.onload=()=>setTimeout(()=>window.print(),300)</script></html>`)
        printWindow.document.close()
        return
      }
      const blob = await downloadMockInterviewReport(session.session_id)
      const href = URL.createObjectURL(blob); const anchor = document.createElement('a')
      anchor.href = href; anchor.download = 'conseils-entretien.pdf'; anchor.click(); URL.revokeObjectURL(href)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not download the coaching sheet.') }
    finally { setPending(false) }
  }

  function speakQuestion() {
    if (!currentQuestion || !('speechSynthesis' in window)) { setError('Speech playback is unavailable in this browser.'); return }
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(currentQuestion.prompt)
    utterance.lang = locale[language]
    window.speechSynthesis.speak(utterance)
  }

  if (!localStorage.getItem('mahara_access_token')) return <div className="mock-interview-page"><section className="mock-card mock-empty"><h2>Sign in to practice privately</h2><p>Your interview responses are only available in your candidate account.</p><Link className="primary-btn" to="/signin">Sign in</Link></section></div>

  return <div className="mock-interview-page">
    <header className="mock-topbar"><Link to="/dashboard" className="mock-brand"><span className="mock-brand-mark">M</span><span><strong>Mahara Match</strong><small>Candidate space</small></span></Link><span className="module-tag">Candidate</span><span className="mock-concept-badge">Private practice · No score</span></header>
    {error && <div className="mock-alert error" role="alert">{error}</div>}{notice && <div className="mock-alert" role="status">{notice}</div>}

    {mode === 'setup' && <main className="mock-content">
      <section className="mock-privacy-banner"><span aria-hidden="true">◇</span><div><h2>Confidential, supportive practice</h2><p>Your responses are only used to prepare private coaching. They are never shared with employers, used in matching, or treated as a hiring result. Audio is transcribed in memory; the recording is not kept.</p><small>Demo using the configured AI provider. Feedback is approximate; there are no scores, percentages, or rankings.</small></div><span className="mock-privacy-label">You stay in control</span></section>
      <section className="mock-card mock-hero"><div><p className="eyebrow">Oral practice workshop</p><h1>AI mock interview</h1><p className="mock-lead">Prepare for real conversations at work. Practice in French, Modern Standard Arabic, or Tunisian Derja, then get practical suggestions grounded in what you said.</p></div><aside><strong>Coaching, never grading</strong><p>Your practice does not change your Mahara Match profile or job recommendations.</p></aside></section>
      <div className="mock-setup-grid">
        <form className="mock-card mock-form" onSubmit={(event) => void begin(event)}>
          <label>Target job or occupation<select value={occupationCode || (customTitle ? '__custom' : '')} onChange={(event) => { setTargetOfferId(null); if (event.target.value === '__custom') { setOccupationCode(''); return } setOccupationCode(event.target.value); setCustomTitle('') }}><option value="">Choose an occupation</option>{occupations.map((item) => <option value={item.code} key={item.code}>{item.title_fr}</option>)}<option value="__custom">Enter a job title</option></select></label>
          {(!occupationCode) && <label>Job title<input required minLength={2} maxLength={200} value={customTitle} onChange={(event) => { setTargetOfferId(null); setCustomTitle(event.target.value) }} placeholder="For example, TIG welder or sales adviser" /></label>}
          {applications.length > 0 && <label>Or practice for one of your applications<select value={targetOfferId ?? ''} onChange={(event) => { const selected = applications.find((item) => item.job_offer_id === event.target.value); if (selected) { setOccupationCode(''); setCustomTitle(selected.title); setTargetOfferId(selected.job_offer_id) } else setTargetOfferId(null) }}><option value="">Select an applied offer</option>{applications.map((item) => <option key={item.application_id} value={item.job_offer_id}>{item.title}</option>)}</select></label>}
          <fieldset><legend>Interview length</legend><div className="mock-choice-row">{[[3,'3 questions','~10 min'],[5,'5 questions','~20 min'],[8,'8 questions','~30 min']].map(([count,label,time]) => <label className={`mock-choice ${questionCount === count ? 'selected' : ''}`} key={count}><input type="radio" name="question-count" checked={questionCount === count} onChange={() => setQuestionCount(Number(count))} /><strong>{label}</strong><small>{time}</small></label>)}</div></fieldset>
          <label>Language<select value={language} onChange={(event) => setLanguage(event.target.value as MockInterview['language'])}><option value="fr">Technical French</option><option value="ar">Modern Standard Arabic</option><option value="derja">Tunisian Derja</option></select></label>
          <div className="mock-consent"><label><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span>I agree to send my selected job title and interview responses to the configured AI service for private coaching. If I select an applied offer, its description and listed skill requirements will also be sent to tailor questions. I understand feedback is approximate and is not shared with employers.</span></label><small>Voice recordings are sent to the configured transcription provider for transcription, then discarded. Unfinished sessions are automatically deleted after 24 hours. Saving a session keeps it in your private space for 30 days. You can delete it at any time.</small></div>
          <button className="primary-btn" disabled={pending || loading || !consent || !targetTitle}>{pending ? 'Preparing questions…' : 'Start private practice'}</button>
        </form>
        <aside className="mock-card mock-instructions"><h2>How practice works</h2><ol><li>Choose a job and language.</li><li>Answer one question at a time by typing or speaking.</li><li>Review and correct every transcription before it is saved.</li><li>Get supportive advice with examples and next steps.</li></ol><p>Microphone access is optional. You can use your keyboard throughout.</p><div className="mock-future-label">Video mirror is a future concept and is not available in this experience.</div></aside>
      </div>
      {loading && <p role="status">Loading your private sessions…</p>}
      {savedItems.length > 0 && <section className="mock-card mock-saved-list"><header><div><p className="eyebrow">Private space</p><h2>Saved practice sessions</h2></div></header>{savedItems.map((item) => <article key={item.session_id}><div><strong>{item.target_title}</strong><small>{item.status === 'completed' ? 'Coaching review ready' : `${item.current_index} of ${item.question_count} questions answered`} · {item.language.toUpperCase()}</small></div><div className="mock-actions"><button type="button" className="secondary-btn" disabled={pending} onClick={() => void resume(item.session_id)}>{item.status === 'completed' ? 'Review advice' : 'Resume'}</button><button type="button" className="ghost-btn" disabled={pending} onClick={() => void deleteSavedSession(item.session_id)}>Delete</button></div></article>)}</section>}
    </main>}

    {mode === 'cockpit' && session && <main className="mock-content">
      <div className="mock-cockpit-heading"><div><p className="eyebrow">Practice in progress</p><h1>{session.target_title}</h1><p>Question {Math.min(session.current_index + 1, session.question_count)} of {session.question_count} · {session.language.toUpperCase()}</p></div><button className="secondary-btn" type="button" onClick={() => setShowExit(true)}>Pause and save</button></div>
      <div className="mock-progress" aria-label={`Question ${session.current_index} of ${session.question_count}`}><span style={{ width: `${Math.max(4, session.current_index / session.question_count * 100)}%` }} /></div>
      {session.current_index >= session.question_count ? <section className="mock-card mock-unavailable"><h2>Your responses are safe</h2><p>The coaching service did not finish this review. Your answers are saved privately for now. Try again when the service is available.</p><button className="primary-btn" type="button" disabled={pending} onClick={() => void retryReview()}>{pending ? 'Preparing advice…' : 'Retry coaching review'}</button></section> : currentQuestion && <div className="mock-cockpit-grid"><section className="mock-card mock-question-card"><div className="mock-question-top"><span>Question {session.current_index + 1}</span><span>{currentQuestion.theme}</span><button className="ghost-btn" type="button" onClick={speakQuestion}>Listen to the question</button></div><h2>{currentQuestion.prompt}</h2>{currentQuestion.follow_up && <details className="mock-followup"><summary>Optional follow-up prompt</summary><p>{currentQuestion.follow_up}</p></details>}<p className="mock-tip">Suggestion: {currentQuestion.tip}</p></section>
        <form className="mock-card mock-answer-form" onSubmit={(event) => void submitAnswer(event)}><div className="mock-answer-heading"><div><h2>Your answer</h2><p>Write it or record a voice response. You can edit the transcription.</p></div></div><div className="mock-recording-controls"><button className={voice.recording ? 'secondary-btn voice-recording' : 'secondary-btn'} type="button" onClick={() => voice.recording ? voice.stop() : void voice.start()} disabled={pending || voice.transcribing}>{voice.recording ? 'Stop recording' : voice.transcribing ? 'Transcribing…' : 'Record answer'}</button>{voice.recording && <span role="status">Recording on this device. Stop when finished.</span>}</div>{voice.error && <p className="mock-inline-error" role="alert">{voice.error} You can retry the microphone or type your answer.</p>}<label className="sr-only" htmlFor="mock-answer">Your interview answer</label><textarea id="mock-answer" required minLength={1} maxLength={8000} rows={9} value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="Structure your answer: context, challenge, action, result…"/><div className="mock-answer-footer"><small>{answer.trim().split(/\s+/).filter(Boolean).length} words · Transcription is editable before submission.</small><button className="primary-btn" type="submit" disabled={pending || voice.transcribing || !answer.trim()}>{pending ? 'Saving…' : session.current_index + 1 === session.question_count ? 'Finish and get advice' : 'Save and continue'}</button></div></form></div>}
    </main>}

    {mode === 'feedback' && session?.feedback && <main className="mock-content"><section className="mock-feedback-hero"><p className="eyebrow">Private coaching review</p><h1>Your practice debrief</h1><p>{session.target_title} · {session.question_count} questions reviewed</p><div className="mock-feedback-reassurance">No score, percentage, pass/fail verdict, or ranking is calculated. These suggestions are for practice only.</div></section><section className="mock-card mock-feedback-summary"><h2>Overall guidance</h2><p>{session.feedback.overall_summary}</p></section><div className="mock-topic-grid">{session.feedback.topics.map((topic) => <article className="mock-card mock-topic" key={topic.title}><span className="mock-topic-status">{topic.status}</span><h3>{topic.title}</h3><p>{topic.evidence}</p><strong>Next step</strong><p>{topic.next_step}</p></article>)}</div><section className="mock-card mock-answer-reviews"><h2>Review each answer</h2>{session.feedback.answers.map((item) => <article key={item.question_index}><p className="eyebrow">Question {item.question_index + 1}</p><h3>{session.questions[item.question_index]?.prompt}</h3><p><strong>What worked:</strong> {item.strength}</p><p><strong>Try next:</strong> {item.improvement}</p><p><strong>Possible wording:</strong> {item.example}</p></article>)}</section><div className="mock-feedback-actions"><button className="primary-btn" type="button" disabled={pending} onClick={() => void downloadAdvice()}>Download advice sheet (PDF)</button>{!session.saved && <button className="secondary-btn" type="button" disabled={pending} onClick={() => void saveForLater()}>Save in my private space</button>}<button className="secondary-btn" type="button" disabled={pending} onClick={() => { setSession(null); setMode('setup'); setNotice('Your completed session will be deleted automatically after 24 hours unless you save it.') }}>Return to practice menu</button><button className="ghost-btn" type="button" disabled={pending} onClick={() => void discardSession()}>Delete this session now</button></div></main>}

    {showExit && session && <div className="mock-modal-backdrop" role="presentation"><section className="mock-modal" role="dialog" aria-modal="true" aria-labelledby="mock-exit-title"><h2 id="mock-exit-title">Pause this practice?</h2><p>Previously submitted answers are saved. If you choose to save, the response currently in the editor will also be kept in your private session for 30 days.</p><div className="mock-modal-actions"><button className="secondary-btn" type="button" disabled={pending} onClick={() => setShowExit(false)}>Continue interview</button><button className="primary-btn" type="button" disabled={pending} onClick={() => void saveForLater()}>Save privately for 30 days</button><button className="danger-btn" type="button" disabled={pending} onClick={() => void discardSession()}>Delete responses and quit</button></div></section></div>}
  </div>
}
