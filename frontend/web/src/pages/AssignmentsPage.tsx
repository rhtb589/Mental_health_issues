import { useEffect, useState } from 'react'
import api from '@/lib/api'
import type { Assignment } from '@/lib/types'
import { UserCheck } from 'lucide-react'

export default function AssignmentsPage() {
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/assignments')
      .then(res => setAssignments(res.data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>

  return (
    <div>
      <h1 className="text-2xl font-bold flex items-center gap-2 mb-6">
        <UserCheck className="h-6 w-6" /> Assignments
      </h1>
      <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted">
                <th className="px-4 py-3 text-left font-medium">Patient ID</th>
                <th className="px-4 py-3 text-left font-medium">Provider ID</th>
                <th className="px-4 py-3 text-left font-medium">Provider Role</th>
                <th className="px-4 py-3 text-left font-medium">Active</th>
                <th className="px-4 py-3 text-left font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {assignments.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">No assignments found</td></tr>
              ) : assignments.map(a => (
                <tr key={a.assignment_id} className="border-b last:border-0 hover:bg-muted/50">
                  <td className="px-4 py-3 font-mono text-xs">{a.patient_id.slice(0, 8)}...</td>
                  <td className="px-4 py-3 font-mono text-xs">{a.provider_id.slice(0, 8)}...</td>
                  <td className="px-4 py-3">{a.provider_role}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${a.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                      {a.active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{a.created_at ? new Date(a.created_at).toLocaleDateString() : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
