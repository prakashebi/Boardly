import type { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LogOut, LayoutGrid, ChevronRight, Search } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'

interface Crumb {
  label: string
  href?: string
}

interface Props {
  breadcrumbs?: Crumb[]
  actions?: ReactNode
}

export default function Navbar({ breadcrumbs = [], actions }: Props) {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="flex h-12 items-center justify-between bg-indigo-700 px-4 text-white shadow-md flex-shrink-0">
      <div className="flex items-center gap-2 text-sm">
        <Link to="/" className="flex items-center gap-1.5 font-semibold text-white hover:text-indigo-200">
          <LayoutGrid size={18} />
          <span>Boardly</span>
        </Link>
        {breadcrumbs.map((crumb, i) => (
          <span key={i} className="flex items-center gap-2">
            <ChevronRight size={14} className="text-indigo-300" />
            {crumb.href ? (
              <Link to={crumb.href} className="text-indigo-200 hover:text-white">
                {crumb.label}
              </Link>
            ) : (
              <span className="text-white">{crumb.label}</span>
            )}
          </span>
        ))}
      </div>

      {user && (
        <div className="flex items-center gap-3">
          {actions}
          <Link
            to="/search"
            className="flex items-center gap-1 rounded px-2 py-1 text-sm text-indigo-200 hover:bg-indigo-600 hover:text-white"
            title="Search"
          >
            <Search size={15} />
            <span>Search</span>
          </Link>
          <span className="text-sm text-indigo-200">{user.username}</span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1 rounded px-2 py-1 text-sm text-indigo-200 hover:bg-indigo-600 hover:text-white"
          >
            <LogOut size={15} />
            <span>Logout</span>
          </button>
        </div>
      )}
    </nav>
  )
}
