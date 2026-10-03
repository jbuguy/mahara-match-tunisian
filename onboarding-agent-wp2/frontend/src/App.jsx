import { useState } from 'react'
import { creerSession } from './api.js'
import FinalScreen from './components/FinalScreen.jsx'
import QuestionScreen from './components/QuestionScreen.jsx'
import WelcomeScreen from './components/WelcomeScreen.jsx'

function App() {
  const [screen, setScreen] = useState('welcome')
  const [sessionId, setSessionId] = useState('')
  const [question, setQuestion] = useState(null)
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState('')

  async function startSession() {
    setStarting(true)
    setStartError('')
    try {
      const session = await creerSession()
      setSessionId(session.session_id)
      setQuestion(session.question)
      setScreen('question')
    } catch (error) {
      setStartError(error.message)
    } finally {
      setStarting(false)
    }
  }

  if (screen === 'question' && question) {
    return (
      <QuestionScreen
        key={question.id}
        sessionId={sessionId}
        question={question}
        onNext={setQuestion}
        onFinish={() => setScreen('final')}
      />
    )
  }

  if (screen === 'final') {
    return <FinalScreen sessionId={sessionId} onRestart={startSession} restarting={starting} restartError={startError} />
  }

  return <WelcomeScreen onStart={startSession} loading={starting} error={startError} />
}

export default App
