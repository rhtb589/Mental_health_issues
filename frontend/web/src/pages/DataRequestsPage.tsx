import { useEffect, useState } from 'react'
import api from '@/lib/api'
import type { DataRequest } from '@/lib/types'
import { Trash2 } from 'lucide-react'

export default function DataRequestsPage() {
  const [requests, setRequests] = useState<DataRequest[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/data-requests')
      .then(res => setRequests(res.data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>

  return (
    <div>
      <h1 className="text-2xl font-bold flex items-center gap-2 mb-6">
        <Trash2 className="h-6 w-6" /> Data Subject Requests
      </h1>
      <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted">
                <th className="px-4 py-3 text-left font-medium">User ID</th>
                <th className="px-4 py-3 text-left font-medium">Type</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-left font-medium">Reason</th>
                <th className="px-4 py-3 text-left font-medium">Requested</th>
                <th className="px-4 py-3 text-left font-medium">Processed</th>
              </tr>
            </thead>
            <tbody>
              {requests.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No data requests found</td></tr>
              ) : requests.map(r => (
                <tr key={r.request_id} className="border-b last:border-0 hover:bg-muted/50">
                  <td className="px-4 py-3 font-mono text-xs">{r.user_id.slice(0, 8)}...</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${r.request_type === 'delete' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}`}>
                      {r.request_type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${r.status === 'done' ? 'bg-green-100 text-green-800' : r.status === 'pending' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 max-w-xs truncate">{r.reason || '-'}</td>
                  <td className="px-4 py-3 text-muted-foreground">{r.requested_at ? new Date(r.requested_at).toLocaleDateString() : '-'}</td>
                  <td className="px-4 py-3 text-muted-foreground">{r.processed_at ? new Date(r.processed_at).toLocaleDateString() : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
