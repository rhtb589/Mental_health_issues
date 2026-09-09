import { useEffect, useState } from 'react'
import api from '@/lib/api'
import type { AuditLog } from '@/lib/types'
import { Shield } from 'lucide-react'

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/audit/logs')
      .then(res => setLogs(res.data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>

  return (
    <div>
      <h1 className="text-2xl font-bold flex items-center gap-2 mb-6">
        <Shield className="h-6 w-6" /> Audit Logs
      </h1>
      <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted">
                <th className="px-4 py-3 text-left font-medium">Seq</th>
                <th className="px-4 py-3 text-left font-medium">Event Type</th>
                <th className="px-4 py-3 text-left font-medium">Actor</th>
                <th className="px-4 py-3 text-left font-medium">Subject</th>
                <th className="px-4 py-3 text-left font-medium">Resource</th>
                <th className="px-4 py-3 text-left font-medium">Time</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No audit logs found</td></tr>
              ) : logs.map(l => (
                <tr key={l.event_id} className="border-b last:border-0 hover:bg-muted/50">
                  <td className="px-4 py-3 font-mono text-xs">{l.seq}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex rounded-full bg-muted px-2 py-1 text-xs font-medium">{l.event_type}</span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{l.actor_user_id?.slice(0, 8)}...</td>
                  <td className="px-4 py-3 font-mono text-xs">{l.subject_user_id?.slice(0, 8)}...</td>
                  <td className="px-4 py-3">{l.resource_type}/{l.resource_id?.slice(0, 8)}</td>
                  <td className="px-4 py-3 text-muted-foreground">{l.occurred_at ? new Date(l.occurred_at).toLocaleString() : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
