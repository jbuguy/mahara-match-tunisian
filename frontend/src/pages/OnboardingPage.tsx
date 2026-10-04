import { useState } from 'react'

import { requestJson } from '../lib/api'

const onboardingPayload = {
  id: 'cand_001',
  first_name: 'Nadia',
  last_name: 'Ben Ali',
  email: 'nadia@example.com',
  headline: 'Product designer with 6 years of experience',
  summary: 'Design systems and user research for B2B SaaS teams.',
  location: 'Tunis',
  skills: [
    { code: 'UX', name: 'User Experience', level: 'expert' },
    { code: 'FIGMA', name: 'Figma', level: 'expert' },
    { code: 'PRODUCT', name: 'Product design', level: 'advanced' },
  ],
}

export function OnboardingPage() {
  const [result, setResult] = useState('')

  async function validateOnboarding() {
    const response = await requestJson<Record<string, unknown>>('/platform/integrations/wp2/onboard', {
      method: 'POST',
      body: JSON.stringify(onboardingPayload),
    })

    setResult(JSON.stringify(response, null, 2))
  }

  return (
    <div className="stacked-view">
      <header className="panel-header">
        <div>
          <p className="eyebrow">WP2</p>
          <h2>Onboarding agent</h2>
        </div>
      </header>

      <div className="agent-panel">
        <div className="agent-header">
          <div className="agent-avatar">AI</div>
          <div>
            <strong>Mahara onboarding assistant</strong>
            <small>Guiding the candidate through profile setup</small>
          </div>
        </div>

        <div className="question-box">
          <span>Current prompt</span>
          <p>Can you summarize my recent roles and highlight the most relevant skills for product and design roles?</p>
        </div>

        <div className="agent-answers">
          <div className="answer-card">
            <h4>Recommended next step</h4>
            <p>Import your CV or complete the role snapshot to unlock a personalized skill graph.</p>
          </div>
          <div className="answer-card">
            <h4>Suggested skills</h4>
            <ul>
              <li>Product strategy</li>
              <li>Figma and design systems</li>
              <li>User research</li>
            </ul>
          </div>
        </div>

        <button className="primary-btn" type="button" onClick={validateOnboarding}>
          Validate onboarding profile
        </button>
        {result && <pre>{result}</pre>}
      </div>
    </div>
  )
}
