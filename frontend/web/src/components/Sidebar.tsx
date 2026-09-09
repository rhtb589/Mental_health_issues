import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from './AuthProvider'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  ClipboardList,
  Users,
  FileText,
  Shield,
  UserCheck,
  Trash2,
  LogOut,
  Activity,
  MessageSquare,
} from 'lucide-react'

const navItems = [
  { to: '/chat', label: 'Chat', icon: MessageSquare, admin: false },
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, admin: true },
  { to: '/screener', label: 'Screening', icon: ClipboardList, admin: false },
  { to: '/assessments', label: 'Assessments', icon: Activity, admin: false },
  { to: '/users', label: 'Users', icon: Users, admin: true },
  { to: '/audit', label: 'Audit Logs', icon: Shield, admin: true },
  { to: '/consents', label: 'Consents', icon: FileText, admin: true },
  { to: '/assignments', label: 'Assignments', icon: UserCheck, admin: true },
  { to: '/data-requests', label: 'Data Requests', icon: Trash2, admin: true },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const filtered = navItems.filter(item => !item.admin || user?.role === 'admin')

  return (
    <aside className="flex h-screen w-64 flex-col border-r bg-card">
      <div className="flex h-14 items-center border-b px-4">
        <Activity className="mr-2 h-6 w-6 text-primary" />
        <span className="text-lg font-semibold">MH Care</span>
      </div>
      <nav className="flex-1 space-y-1 p-2">
        {filtered.map(item => (
          <Link
            key={item.to}
            to={item.to}
            className={cn(
              "flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
              location.pathname === item.to
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground"
            )}
          >
            <item.icon className="mr-2 h-4 w-4" />
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="border-t p-4">
        <div className="mb-2 text-xs text-muted-foreground">
          {user?.email} ({user?.role})
        </div>
        <button
          onClick={handleLogout}
          className="flex w-full items-center rounded-md px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        >
          <LogOut className="mr-2 h-4 w-4" />
          Logout
        </button>
      </div>
    </aside>
  )
}
