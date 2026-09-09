import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/components/AuthProvider'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import Layout from '@/components/Layout'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import DashboardPage from '@/pages/DashboardPage'
import ScreenerPage from '@/pages/ScreenerPage'
import AssessmentsPage from '@/pages/AssessmentsPage'
import UsersPage from '@/pages/UsersPage'
import AuditPage from '@/pages/AuditPage'
import ConsentsPage from '@/pages/ConsentsPage'
import AssignmentsPage from '@/pages/AssignmentsPage'
import DataRequestsPage from '@/pages/DataRequestsPage'
import ChatPage from '@/pages/ChatPage'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/chat" replace />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="dashboard" element={<ProtectedRoute adminOnly><DashboardPage /></ProtectedRoute>} />
            <Route path="screener" element={<ScreenerPage />} />
            <Route path="assessments" element={<AssessmentsPage />} />
            <Route path="users" element={<ProtectedRoute adminOnly><UsersPage /></ProtectedRoute>} />
            <Route path="audit" element={<ProtectedRoute adminOnly><AuditPage /></ProtectedRoute>} />
            <Route path="consents" element={<ProtectedRoute adminOnly><ConsentsPage /></ProtectedRoute>} />
            <Route path="assignments" element={<ProtectedRoute adminOnly><AssignmentsPage /></ProtectedRoute>} />
            <Route path="data-requests" element={<ProtectedRoute adminOnly><DataRequestsPage /></ProtectedRoute>} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
