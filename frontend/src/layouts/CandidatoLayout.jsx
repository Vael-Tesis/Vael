import { Outlet } from 'react-router-dom'
import { motion } from 'framer-motion'

export default function CandidatoLayout() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-page)' }}>
      <nav style={{
        background: 'var(--bg-card)', borderBottom: '1px solid var(--border)',
        padding: '0 24px', height: 52, display: 'flex', alignItems: 'center',
      }}>
        <div style={{
          width: 26, height: 26, background: 'var(--text-primary)',
          borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginRight: 8,
        }}>
          <span style={{ color: 'var(--bg-card)', fontSize: 10, fontWeight: 600 }}>VA</span>
        </div>
        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>VAEL</span>
      </nav>

      <motion.main
        key={window.location.pathname}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.18 }}
      >
        <Outlet />
      </motion.main>
    </div>
  )
}