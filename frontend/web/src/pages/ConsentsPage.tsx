import { useEffect, useState } from 'react'
import api from '@/lib/api'
import type { ConsentRecord } from '@/lib/types'
import { FileText } from 'lucide-react'

export default function ConsentsPage() {
  const [consents, setConsents] = useState<ConsentRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/consent')
      .then(res => setConsents(res.data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>

  return (
    <div>
      <h1 className="text-2xl font-bold flex items-center gap-2 mb-6">
        <FileText className="h-6 w-6" /> Consent Records
      </h1>
      <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted">
                <th className="px-4 py-3 text-left font-medium">Purpose</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-left font-medium">Version</th>
                <th className="px-4 py-3 text-left font-medium">Recorded</th>
                <th className="px-4 py-3 text-left font-medium">Withdrawn</th>
                <th className="px-4 py-3 text-left font-medium">Active</th>
              </tr>
            </thead>
            <tbody>
              {consents.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No consent records found</td></tr>
              ) : consents.map(c => (
                <tr key={c.consent_id} className="border-b last:border-0 hover:bg-muted/50">
                  <td className="px-4 py-3 font-medium">{c.purpose}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${c.status === 'given' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">{c.consent_text_version}</td>
                  <td className="px-4 py-3 text-muted-foreground">{new Date(c.recorded_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-muted-foreground">{c.withdrawn_at ? new Date(c.withdrawn_at).toLocaleDateString() : '-'}</td>
                  <td className="px-4 py-3">{c.is_active ? 'Yes' : 'No'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
