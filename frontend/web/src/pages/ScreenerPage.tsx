import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'
import { ClipboardList, AlertTriangle, CheckCircle2 } from 'lucide-react'

const SCREENERS = [
  { id: 'PHQ9', name: 'PHQ-9 (Depression)', description: 'Patient Health Questionnaire-9' },
  { id: 'GAD7', name: 'GAD-7 (Anxiety)', description: 'Generalized Anxiety Disorder-7' },
  { id: 'PHQ4', name: 'PHQ-4 (Brief)', description: 'Patient Health Questionnaire-4' },
  { id: 'SAFE-T', name: 'SAFE-T / C-SSRS (Suicide Risk)', description: 'Suicide Assessment Five-Step Evaluation' },
]

const PHQ9_QUESTIONS = [
  { id: 'PHQ9_01', text: 'Little interest or pleasure in doing things' },
  { id: 'PHQ9_02', text: 'Feeling down, depressed, or hopeless' },
  { id: 'PHQ9_03', text: 'Trouble falling or staying asleep, or sleeping too much' },
  { id: 'PHQ9_04', text: 'Feeling tired or having little energy' },
  { id: 'PHQ9_05', text: 'Poor appetite or overeating' },
  { id: 'PHQ9_06', text: 'Feeling bad about yourself — or that you are a failure' },
  { id: 'PHQ9_07', text: 'Trouble concentrating on things' },
  { id: 'PHQ9_08', text: 'Moving or speaking too slowly, or being fidgety/restless' },
  { id: 'PHQ9_09', text: 'Thoughts that you would be better off dead or of hurting yourself', safety: true },
]

const FREQUENCY_OPTIONS = [
  { value: 0, label: 'Not at all' },
  { value: 1, label: 'Several days' },
  { value: 2, label: 'More than half the days' },
  { value: 3, label: 'Nearly every day' },
]

const GAD7_QUESTIONS = [
  { id: 'GAD7_01', text: 'Feeling nervous, anxious or on edge' },
  { id: 'GAD7_02', text: 'Not being able to stop or control worrying' },
  { id: 'GAD7_03', text: 'Worrying too much about different things' },
  { id: 'GAD7_04', text: 'Trouble relaxing' },
  { id: 'GAD7_05', text: 'Being so restless that it is hard to sit still' },
  { id: 'GAD7_06', text: 'Becoming easily annoyed or irritable' },
  { id: 'GAD7_07', text: 'Feeling afraid as if something awful might happen' },
]

const PHQ4_QUESTIONS = [
  { id: 'PHQ4_01', text: 'Feeling nervous, anxious or on edge' },
  { id: 'PHQ4_02', text: 'Not being able to stop or control worrying' },
  { id: 'PHQ4_03', text: 'Little interest or pleasure in doing things' },
  { id: 'PHQ4_04', text: 'Feeling down, depressed, or hopeless' },
]

const SAFET_RISK_FACTORS = {
  'Activating Events': ['Recent losses or significant negative events', 'Pending incarceration or homelessness', 'Current or pending isolation'],
  'Treatment History': ['Previous psychiatric diagnosis and treatments', 'Hopeless or dissatisfied with treatment', 'Non-compliant with treatment', 'Not receiving treatment', 'Insomnia'],
  'Clinical Status': ['Hopelessness', 'Major depressive episode', 'Mixed affect episode', 'Command hallucinations to hurt self', 'Chronic physical pain', 'Highly impulsive behavior', 'Substance abuse or dependence', 'Agitation or severe anxiety', 'Perceived burden on family', 'Homicidal ideation', 'Aggressive behavior', 'Refuses safety plan', 'Sexual abuse (lifetime)', 'Family history of suicide', 'Access to lethal methods'],
}

const SAFET_PROTECTIVE_FACTORS = {
  'Internal': ['Fear of death or dying due to pain', 'Identifies reasons for living'],
  'External': ['Belief that suicide is immoral', 'Responsibility to family', 'Supportive social network', 'Engaged in work or school'],
}

const SAFET_IDEATION_QUESTIONS = [
  { id: 'SAFE-T_SI_1', text: 'Wish to be dead', prompt: 'Have you wished you were dead or wished you could go to sleep and not wake up?' },
  { id: 'SAFE-T_SI_2', text: 'Current suicidal thoughts', prompt: 'Have you actually had any thoughts of killing yourself?' },
  { id: 'SAFE-T_SI_3', text: 'Suicidal thoughts with method', prompt: 'Have you been thinking about how you might do this?' },
  { id: 'SAFE-T_SI_4', text: 'Suicidal intent without specific plan', prompt: 'Have you had these thoughts and had some intention of acting on them?' },
  { id: 'SAFE-T_SI_5', text: 'Intent with plan', prompt: 'Have you started to work out or worked out the details of how to kill yourself?' },
]

const SAFET_BEHAVIOR_QUESTION = { id: 'SAFE-T_SB', text: 'Suicidal Behavior', prompt: 'Have you ever done anything, started to do anything, or prepared to do anything to end your life?' }

function getRequiredQuestionIds(screenerId: string): string[] {
  switch (screenerId) {
    case 'PHQ9':
      return PHQ9_QUESTIONS.map(q => q.id)
    case 'GAD7':
      return GAD7_QUESTIONS.map(q => q.id)
    case 'PHQ4':
      return PHQ4_QUESTIONS.map(q => q.id)
    case 'SAFE-T':
      return [
        ...Object.keys(SAFET_RISK_FACTORS).map(g => `risk_${g}`),
        ...Object.keys(SAFET_PROTECTIVE_FACTORS).map(g => `protect_${g}`),
        ...SAFET_IDEATION_QUESTIONS.map(q => q.id),
        SAFET_BEHAVIOR_QUESTION.id,
      ]
    default:
      return []
  }
}

export default function ScreenerPage() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const [selectedScreener, setSelectedScreener] = useState('')
  const [responses, setResponses] = useState<Record<string, any>>({})
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')
  const [step, setStep] = useState<'select' | 'form' | 'result'>('select')

  // Auto-select instrument from URL query parameter
  useEffect(() => {
    const instrument = searchParams.get('instrument')
    if (instrument && SCREENERS.some(s => s.id === instrument)) {
      setSelectedScreener(instrument)
      setStep('form')
    }
  }, [searchParams])

  const handleSelect = (id: string) => {
    setSelectedScreener(id)
    setResponses({})
    setResult(null)
    setError('')
    setStep('form')
  }

  const setResponse = (questionId: string, value: any) => {
    setResponses(prev => ({ ...prev, [questionId]: value }))
  }

  const toggleMultiResponse = (questionId: string, item: string) => {
    setResponses(prev => {
      const current = prev[questionId] || []
      const updated = current.includes(item)
        ? current.filter((i: string) => i !== item)
        : [...current, item]
      return { ...prev, [questionId]: updated }
    })
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    setError('')

    const requiredIds = getRequiredQuestionIds(selectedScreener)
    const missing = requiredIds.filter(id => {
      const v = responses[id]
      return v === undefined || v === '' || (Array.isArray(v) && v.length === 0)
    })
    if (missing.length > 0) {
      setError(`Please answer all questions before submitting (${missing.length} remaining).`)
      setSubmitting(false)
      return
    }

    try {
      await api.post('/consent/give', {
        purpose: 'screening',
        consent_text: 'I consent to participate in mental health screening.',
      }).catch(() => {})

      await api.post('/consent/give', {
        purpose: 'storage',
        consent_text: 'I consent to storage of my screening results.',
      }).catch(() => {})

      const assessmentRes = await api.post('/assessments', {
        instrument_id: selectedScreener,
      })
      const assessmentId = assessmentRes.data.assessment_id

      for (const [questionId, value] of Object.entries(responses)) {
        if (value !== undefined && value !== '' && (!Array.isArray(value) || value.length > 0)) {
          await api.post(`/assessments/${assessmentId}/responses`, {
            question_id: questionId,
            response_value: value,
          })
        }
      }

      const { calculateScore } = await import('@/lib/scoring')
      const scoreResult = calculateScore(selectedScreener, responses)

      await api.post(`/assessments/${assessmentId}/finalize`, {
        score: scoreResult.score,
        interpretation: scoreResult.interpretation,
        high_risk: scoreResult.high_risk,
        high_risk_detail: JSON.stringify(scoreResult.details),
      })

      setResult(scoreResult)
      setStep('select')
      setSelectedScreener('')
      setResponses({})
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Submission failed')
    } finally {
      setSubmitting(false)
    }
  }

  const renderFrequencyQuestion = (q: { id: string; text: string; safety?: boolean }) => (
    <div key={q.id} className="rounded-lg border p-4">
      <p className="font-medium">
        {q.text}
        {q.safety && <span className="ml-2 inline-flex items-center rounded bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800"><AlertTriangle className="mr-1 h-3 w-3" />Safety</span>}
      </p>
      <div className="mt-3 space-y-2">
        {FREQUENCY_OPTIONS.map(opt => (
          <label key={opt.value} className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name={q.id}
              value={opt.value}
              checked={responses[q.id] === opt.value}
              onChange={() => setResponse(q.id, opt.value)}
              className="h-4 w-4"
            />
            <span className="text-sm">{opt.label}</span>
          </label>
        ))}
      </div>
    </div>
  )

  const renderYesNoQuestion = (q: { id: string; text: string; prompt: string }) => (
    <div key={q.id} className="rounded-lg border p-4">
      <p className="font-medium">{q.text}</p>
      <p className="mt-1 text-sm text-muted-foreground italic">"{q.prompt}"</p>
      <div className="mt-3 flex gap-4">
        {['yes', 'no'].map(opt => (
          <label key={opt} className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name={q.id}
              value={opt}
              checked={responses[q.id] === opt}
              onChange={() => setResponse(q.id, opt)}
              className="h-4 w-4"
            />
            <span className="text-sm capitalize">{opt}</span>
          </label>
        ))}
      </div>
    </div>
  )

  const renderMultiChoice = (groupId: string, groupLabel: string, items: string[]) => (
    <div key={groupId} className="rounded-lg border p-4">
      <p className="font-medium">{groupLabel}</p>
      <div className="mt-3 space-y-2">
        {items.map(item => (
          <label key={item} className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={(responses[groupId] || []).includes(item)}
              onChange={() => toggleMultiResponse(groupId, item)}
              className="mt-0.5 h-4 w-4"
            />
            <span className="text-sm">{item}</span>
          </label>
        ))}
      </div>
    </div>
  )

  const renderForm = () => {
    switch (selectedScreener) {
      case 'PHQ9':
        return (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">Over the last 2 weeks, how often have you been bothered by any of the following problems?</p>
            {PHQ9_QUESTIONS.map(renderFrequencyQuestion)}
          </div>
        )
      case 'GAD7':
        return (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">Over the last 2 weeks, how often have you been bothered by the following problems?</p>
            {GAD7_QUESTIONS.map(renderFrequencyQuestion)}
          </div>
        )
      case 'PHQ4':
        return (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">Over the last 2 weeks, how often have you been bothered by the following problems?</p>
            {PHQ4_QUESTIONS.map(renderFrequencyQuestion)}
          </div>
        )
      case 'SAFE-T':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold">Step 1: Risk Factors</h3>
              <p className="text-sm text-muted-foreground">Select all applicable risk factors.</p>
              <div className="mt-3 space-y-3">
                {Object.entries(SAFET_RISK_FACTORS).map(([group, items]) =>
                  renderMultiChoice(`risk_${group}`, group, items)
                )}
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold">Step 2: Protective Factors</h3>
              <p className="text-sm text-muted-foreground">Select all applicable protective factors.</p>
              <div className="mt-3 space-y-3">
                {Object.entries(SAFET_PROTECTIVE_FACTORS).map(([group, items]) =>
                  renderMultiChoice(`protect_${group}`, group, items)
                )}
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold">Step 3: C-SSRS Suicidal Ideation</h3>
              <p className="text-sm text-muted-foreground">Assessed for the recent month.</p>
              <div className="mt-3 space-y-3">
                {SAFET_IDEATION_QUESTIONS.map(renderYesNoQuestion)}
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold">Step 3: C-SSRS Suicidal Behavior</h3>
              <div className="mt-3">
                {renderYesNoQuestion(SAFET_BEHAVIOR_QUESTION)}
              </div>
            </div>
          </div>
        )
      default:
        return null
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <ClipboardList className="h-6 w-6" />
          Mental Health Screening
        </h1>
        <p className="text-muted-foreground">Select a screening instrument to begin.</p>
      </div>

      {step === 'select' && (
        <div className="grid gap-4 sm:grid-cols-2">
          {SCREENERS.map(s => (
            <button
              key={s.id}
              onClick={() => handleSelect(s.id)}
              className="rounded-lg border bg-card p-6 text-left shadow-sm transition-all hover:border-primary hover:shadow-md"
            >
              <h3 className="font-semibold">{s.name}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{s.description}</p>
            </button>
          ))}
        </div>
      )}

      {step === 'form' && (
        <div>
          <button onClick={() => { setStep('select'); setSelectedScreener(''); }} className="mb-4 text-sm text-muted-foreground hover:text-foreground">
            &larr; Back to selection
          </button>
          <h2 className="text-xl font-semibold mb-4">
            {SCREENERS.find(s => s.id === selectedScreener)?.name}
          </h2>
          {error && (
            <div className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
          )}
          {renderForm()}
          <div className="mt-6 flex justify-end">
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="rounded-md bg-primary px-6 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : 'Submit Screening'}
            </button>
          </div>
        </div>
      )}

      {step === 'result' && result && (
        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle2 className="h-6 w-6 text-green-600" />
            <h2 className="text-xl font-semibold">Screening Complete</h2>
          </div>
          <div className="space-y-3">
            <div className="rounded-md bg-muted p-4">
              <p className="text-sm font-medium text-muted-foreground">Instrument</p>
              <p className="font-semibold">{SCREENERS.find(s => s.id === selectedScreener)?.name}</p>
            </div>
            <div className="rounded-md bg-muted p-4">
              <p className="text-sm font-medium text-muted-foreground">Score</p>
              <p className="font-semibold text-2xl">{typeof result.score === 'object' ? JSON.stringify(result.score) : result.score}</p>
            </div>
            <div className="rounded-md bg-muted p-4">
              <p className="text-sm font-medium text-muted-foreground">Interpretation</p>
              <p className="font-semibold">{result.interpretation}</p>
            </div>
            {result.high_risk && (
              <div className="rounded-md bg-red-50 border border-red-200 p-4">
                <p className="flex items-center gap-2 font-semibold text-red-800">
                  <AlertTriangle className="h-5 w-5" />
                  High Risk Detected
                </p>
                <p className="mt-1 text-sm text-red-700">This screening flagged potential high-risk indicators. Clinical review is recommended.</p>
              </div>
            )}
          </div>
          <button
            onClick={() => { setStep('select'); setSelectedScreener(''); setResult(null); setResponses({}); }}
            className="mt-6 rounded-md bg-primary px-6 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Done
          </button>
        </div>
      )}
    </div>
  )
}
