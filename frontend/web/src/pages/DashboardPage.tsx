import { useEffect, useState } from 'react'
import api from '@/lib/api'
import type { DashboardStats } from '@/lib/types'
import { LayoutDashboard, Users, ClipboardList, AlertTriangle, FileCheck } from 'lucide-react'

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/dashboard/stats')
      .then(res => setStats(res.data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>
  if (!stats) return <div className="text-center py-12 text-muted-foreground">Failed to load dashboard</div>

  const cards = [
    { label: 'Total Users', value: stats.total_users, icon: Users, color: 'text-blue-600' },
    { label: 'Active Users', value: stats.active_users, icon: Users, color: 'text-green-600' },
    { label: 'Total Assessments', value: stats.total_assessments, icon: ClipboardList, color: 'text-purple-600' },
    { label: 'Completed', value: stats.completed_assessments, icon: FileCheck, color: 'text-green-600' },
    { label: 'High Risk', value: stats.high_risk_count, icon: AlertTriangle, color: 'text-red-600' },
    { label: 'Active Consents', value: stats.active_consents, icon: FileCheck, color: 'text-blue-600' },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold flex items-center gap-2 mb-6">
        <LayoutDashboard className="h-6 w-6" /> Dashboard
      </h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map(card => (
          <div key={card.label} className="rounded-lg border bg-card p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-muted-foreground">{card.label}</p>
              <card.icon className={`h-5 w-5 ${card.color}`} />
            </div>
            <p className="mt-2 text-3xl font-bold">{card.value}</p>
          </div>
        ))}
      </div>
      {stats.by_instrument.length > 0 && (
        <div className="mt-8 rounded-lg border bg-card p-6 shadow-sm">
          <h2 className="text-lg font-semibold mb-4">Assessments by Instrument</h2>
          <div className="space-y-3">
            {stats.by_instrument.map(inst => (
              <div key={inst.instrument_id} className="flex items-center justify-between rounded-md bg-muted px-4 py-3">
                <span className="font-medium">{inst.instrument_id}</span>
                <div className="flex gap-4 text-sm">
                  <span>{inst.total} total</span>
                  {inst.high_risk > 0 && (
                    <span className="text-red-600 font-medium">{inst.high_risk} high risk</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
