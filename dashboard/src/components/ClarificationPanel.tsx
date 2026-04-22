import { useState, useCallback } from 'react'
import { send, sessionId } from '../ws'
import type { ClarificationState } from '../types'

interface Props {
  state: ClarificationState
  onDismiss: () => void
}

export default function ClarificationPanel({ state, onDismiss }: Props) {
  const [answers, setAnswers] = useState<Record<string, string>>(
    () => Object.fromEntries(state.questions.map(q => [q.id, '']))
  )
  const [submitted, setSubmitted] = useState(false)

  const setAnswer = useCallback((id: string, val: string) => {
    setAnswers(prev => ({ ...prev, [id]: val }))
  }, [])

  const handleSubmit = useCallback(() => {
    const payload = state.questions.map(q => ({
      id: q.id,
      question: q.question,
      answer: answers[q.id] || '',
    }))
    send({
      type: 'clarification_answers',
      payload: { answers: payload },
      session_id: sessionId(),
      timestamp: new Date().toISOString(),
    })
    setSubmitted(true)
    onDismiss()
  }, [answers, state.questions, onDismiss])

  const handleSkip = useCallback(() => {
    send({
      type: 'clarification_answers',
      payload: { answers: [] },
      session_id: sessionId(),
      timestamp: new Date().toISOString(),
    })
    onDismiss()
  }, [onDismiss])

  const allAnswered = state.questions.every(q => answers[q.id]?.trim())

  return (
    <div style={{
      position: 'absolute', inset: 0, zIndex: 100,
      background: 'rgba(5, 8, 14, 0.88)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      backdropFilter: 'blur(3px)',
    }}>
      <div style={{
        background: '#0a0f1a',
        border: '1px solid #2a4a6a',
        borderRadius: 12,
        width: '100%', maxWidth: 640,
        maxHeight: '85vh',
        display: 'flex', flexDirection: 'column',
        boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid #1a2a3a',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#8acce0' }}>
              Clarification Needed
            </div>
            <div style={{ fontSize: 11, color: '#3a6a7a', marginTop: 2 }}>
              Answer to sharpen the blueprint. Skip to proceed with best-effort.
            </div>
          </div>
          <div style={{
            background: '#1a2a4a', border: '1px solid #2a4a7a',
            borderRadius: 20, padding: '3px 10px',
            fontSize: 10, color: '#4a8aaa',
          }}>
            {state.questions.length} question{state.questions.length !== 1 ? 's' : ''}
          </div>
        </div>

        {/* Questions */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 20px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          {state.questions.map((q, i) => (
            <div key={q.id}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 6 }}>
                <div style={{
                  width: 20, height: 20, borderRadius: '50%', flexShrink: 0,
                  background: '#1a3a5a', border: '1px solid #2a5a7a',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, color: '#4a9abb', fontWeight: 700, marginTop: 1,
                }}>
                  {i + 1}
                </div>
                <div>
                  <div style={{ fontSize: 12, color: '#cce', lineHeight: 1.4, fontWeight: 600 }}>
                    {q.question}
                  </div>
                  <div style={{ fontSize: 10, color: '#3a6a7a', marginTop: 3 }}>
                    {q.hint}
                  </div>
                </div>
              </div>
              <textarea
                value={answers[q.id] || ''}
                onChange={e => setAnswer(q.id, e.target.value)}
                placeholder="Your answer…"
                rows={2}
                style={{
                  width: '100%', boxSizing: 'border-box',
                  background: '#080e18', border: `1px solid ${answers[q.id]?.trim() ? '#2a5a7a' : '#1a2a3a'}`,
                  borderRadius: 6, color: '#c0d8e8',
                  fontSize: 12, padding: '8px 10px',
                  resize: 'vertical', outline: 'none',
                  fontFamily: 'inherit', lineHeight: 1.5,
                  transition: 'border-color 0.15s',
                }}
                onFocus={e => { e.target.style.borderColor = '#3a7a9a' }}
                onBlur={e => { e.target.style.borderColor = answers[q.id]?.trim() ? '#2a5a7a' : '#1a2a3a' }}
                disabled={submitted}
              />
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{
          padding: '12px 20px',
          borderTop: '1px solid #1a2a3a',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <button
            onClick={handleSkip}
            style={{
              background: 'transparent', border: '1px solid #1a3a4a',
              borderRadius: 6, color: '#3a6a7a',
              fontSize: 12, padding: '6px 16px', cursor: 'pointer',
            }}
          >
            Skip — proceed anyway
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {!allAnswered && (
              <span style={{ fontSize: 10, color: '#2a5a6a' }}>
                {state.questions.filter(q => answers[q.id]?.trim()).length}/{state.questions.length} answered
              </span>
            )}
            <button
              onClick={handleSubmit}
              disabled={submitted}
              style={{
                background: allAnswered ? '#1a4a3a' : '#111a22',
                border: `1px solid ${allAnswered ? '#2a7a4a' : '#1a3a4a'}`,
                borderRadius: 6,
                color: allAnswered ? '#44ff88' : '#2a5a4a',
                fontSize: 12, fontWeight: 700,
                padding: '6px 20px', cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              Submit Answers ▶
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
