import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { toast } from 'sonner'

const NAV = [
  {
    label: 'Principal',
    items: [
      { to: '/dashboard',     icon: '⊞', label: 'Dashboard' },
      { to: '/vacantes',      icon: '◈', label: 'Vacantes' },
      { to: '/candidatos',    icon: '◉', label: 'Candidatos' },
      { to: '/ranking',       icon: '◐', label: 'Ranking' },
      { to: '/banco-talento', icon: '◬', label: 'Banco de talento' },
    ],
  },
  {
    label: 'Evaluaciones',
    items: [
      { to: '/examenes',    icon: '▤', label: 'Exámenes' },
      { to: '/entrevistas', icon: '◎', label: 'Entrevistas IA' },
      { to: '/auditoria',   icon: '◫', label: 'Auditoría' },
    ],
  },
  {
    label: 'Sistema',
    items: [
      { to: '/plantillas', icon: '▦', label: 'Plantillas' },
      { to: '/areas',      icon: '◧', label: 'Áreas' },
      { to: '/usuarios',   icon: '◌', label: 'Usuarios' },
    ],
  },
]

export default function AdminLayout({ theme, setTheme }) {
  const navigate = useNavigate()
  const user = JSON.parse(localStorage.getItem('vael_user') || '{}')

  function handleLogout() {
    localStorage.removeItem('vael_token')
    localStorage.removeItem('vael_user')
    toast.success('Sesión cerrada')
    navigate('/login')
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: 'var(--bg-page)' }}>

      {/* Sidebar */}
      <aside style={{
        width: 212,
        background: 'var(--bg-sidebar)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
      }}>
        {/* Logo */}
        <div style={{
          padding: '16px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}>
          <div style={{
            width: 28, height: 28,
            background: 'var(--text-primary)',
            borderRadius: 6,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--bg-card)',
            fontSize: 11, fontWeight: 600, letterSpacing: '-0.5px',
          }}>VA</div>
          <span style={{ fontWeight: 600, fontSize: 15, color: 'var(--text-primary)' }}>VAEL</span>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: 8, overflowY: 'auto' }}>
          {NAV.map((section) => (
            <div key={section.label}>
              <p style={{
                fontSize: 10, fontWeight: 500,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.07em',
                padding: '10px 8px 4px',
              }}>{section.label}</p>
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  style={({ isActive }) => ({
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '7px 8px',
                    borderRadius: 6,
                    marginBottom: 1,
                    fontSize: 13,
                    fontWeight: isActive ? 500 : 400,
                    color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                    background: isActive ? 'var(--bg-page)' : 'transparent',
                    textDecoration: 'none',
                    transition: 'background 120ms ease, color 120ms ease',
                  })}
                >
                  <span style={{ fontSize: 15 }}>{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div style={{
          padding: 10,
          borderTop: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <div style={{
            width: 28, height: 28, borderRadius: '50%',
            background: 'var(--bg-page)',
            border: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 10, fontWeight: 600, color: 'var(--text-secondary)',
            flexShrink: 0,
          }}>
            {(user.nombre?.[0] || 'U') + (user.apellidos?.[0] || '')}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)', truncate: true }}>
              {user.nombre || 'Usuario'}
            </p>
            <p style={{ fontSize: 10, color: 'var(--text-muted)' }}>{user.rol || 'admin'}</p>
          </div>
          <button
            onClick={() => setTheme(t => t === 'light' ? 'dark' : 'light')}
            title="Cambiar tema"
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-muted)', fontSize: 14, padding: 2,
            }}
          >
            {theme === 'light' ? '◑' : '○'}
          </button>
          <button
            onClick={handleLogout}
            title="Cerrar sesión"
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-muted)', fontSize: 13, padding: 2,
            }}
          >
            ⊗
          </button>
        </div>
      </aside>

      {/* Main */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <motion.main
          key={window.location.pathname}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
          style={{ flex: 1, overflowY: 'auto' }}
        >
          <Outlet />
        </motion.main>
      </div>
    </div>
  )
}