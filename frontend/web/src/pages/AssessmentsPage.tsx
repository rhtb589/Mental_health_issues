import { useEffect, useState } from 'react'
import api from '@/lib/api'
import type { Assessment } from '@/lib/types'
import { Activity, AlertTriangle, ChevronDown, ChevronUp, FileText, Trash2 } from 'lucide-react'

const INSTRUMENT_LABELS: Record<string, string> = {
  PHQ9: 'PHQ-9 Depression',
  GAD7: 'GAD-7 Anxiety',
  PHQ4: 'PHQ-4 Brief',
  'SAFE-T': 'SAFE-T Suicide Risk',
}

const INSTRUMENT_MAX: Record<string, number> = {
  PHQ9: 27,
  GAD7: 21,
  PHQ4: 12,
}

function getSeverityColor(score: number, max: number): string {
  const pct = (score / max) * 100
  if (pct <= 15) return 'text-green-600 bg-green-50'
  if (pct <= 35) return 'text-yellow-600 bg-yellow-50'
  if (pct <= 65) return 'text-orange-600 bg-orange-50'
  return 'text-red-600 bg-red-50'
}

function formatScore(score: any, instrumentId: string): string {
  if (score === null || score === undefined) return '-'
  if (typeof score === 'object') {
    if (instrumentId === 'SAFE-T') {
      const parts: string[] = []
      if (score.ideation_level !== undefined) parts.push(`Ideation L${score.ideation_level}`)
      if (score.risk_factors !== undefined) parts.push(`${score.risk_factors} risk`)
      if (score.protective_factors !== undefined) parts.push(`${score.protective_factors} protective`)
      return parts.join(' | ') || JSON.stringify(score)
    }
    return JSON.stringify(score)
  }
  return String(score)
}

export default function AssessmentsPage() {
  const [assessments, setAssessments] = useState<Assessment[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    api.get('/assessments')
      .then(res => setAssessments(res.data))
      .finally(() => setLoading(false))
  }, [])

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this assessment record?')) return
    setDeletingId(id)
    try {
      await api.delete(`/assessments/${id}`)
      setAssessments(prev => prev.filter(a => a.assessment_id !== id))
    } catch {
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>

  return (
    <div>
      <h1 className="text-2xl font-bold flex items-center gap-2 mb-6">
        <Activity className="h-6 w-6" /> Assessment Evaluations
      </h1>
      <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted">
                <th className="px-4 py-3 text-left font-medium">Screening Instrument</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-left font-medium">Score</th>
                <th className="px-4 py-3 text-left font-medium">Interpretation</th>
                <th className="px-4 py-3 text-left font-medium">Risk</th>
                <th className="px-4 py-3 text-left font-medium">Date</th>
                <th className="px-4 py-3 w-20"></th>
              </tr>
            </thead>
            <tbody>
              {assessments.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">
                  <FileText className="mx-auto h-8 w-8 mb-2 opacity-50" />
                  No assessments yet. Complete a screening to see results here.
                </td></tr>
              ) : assessments.map(a => {
                const max = INSTRUMENT_MAX[a.instrument_id]
                const numScore = typeof a.score === 'number' ? a.score : null
                const severityClass = numScore !== null && max ? getSeverityColor(numScore, max) : ''
                return (
                  <>
                    <tr key={a.assessment_id} className="border-b last:border-0 hover:bg-muted/50">
                      <td className="px-4 py-3">
                        <span className="font-medium">{INSTRUMENT_LABELS[a.instrument_id] || a.instrument_id}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${a.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                          {a.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {numScore !== null && max ? (
                          <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-sm font-bold ${severityClass}`}>
                            {numScore}<span className="text-xs font-normal opacity-70">/{max}</span>
                          </span>
                        ) : (
                          <span className="font-semibold text-sm">{formatScore(a.score, a.instrument_id)}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 max-w-xs truncate">{a.interpretation || '-'}</td>
                      <td className="px-4 py-3">
                        {a.high_risk ? (
                          <span className="inline-flex items-center gap-1 text-red-600">
                            <AlertTriangle className="h-4 w-4" />
                            <span className="text-xs font-medium">High</span>
                          </span>
                        ) : (
                          <span className="text-xs text-green-600">Low</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{new Date(a.started_at).toLocaleDateString()}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          {a.high_risk_detail && (
                            <button
                              onClick={() => setExpandedId(expandedId === a.assessment_id ? null : a.assessment_id)}
                              className="text-muted-foreground hover:text-foreground"
                            >
                              {expandedId === a.assessment_id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                            </button>
                          )}
                          <button
                            onClick={() => handleDelete(a.assessment_id)}
                            disabled={deletingId === a.assessment_id}
                            className="text-muted-foreground hover:text-red-600 disabled:opacity-50"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                    {expandedId === a.assessment_id && a.high_risk_detail && (
                      <tr key={`${a.assessment_id}-detail`}>
                        <td colSpan={7} className="px-4 py-3 bg-red-50 border-b">
                          <p className="text-xs font-medium text-red-800 mb-1">Risk Detail</p>
                          <p className="text-sm text-red-700">{a.high_risk_detail}</p>
                        </td>
                      </tr>
                    )}
                  </>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
