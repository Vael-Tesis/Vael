import { useState, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

// Layouts
import AdminLayout from './layouts/AdminLayout.jsx'
import CandidatoLayout from './layouts/CandidatoLayout.jsx'

// Públicas
import Login from './pages/Login.jsx'
import Postular from './pages/Postular.jsx'

// Portal candidato
import RedireccionadorCandidato from './pages/candidato/RedireccionadorCandidato.jsx'
import Acceso from './pages/candidato/Acceso.jsx'
import ExamenInstrucciones from './pages/candidato/ExamenInstrucciones.jsx'
import Examen from './pages/candidato/Examen.jsx'
import ExamenFinalizado from './pages/candidato/ExamenFinalizado.jsx'
import Progreso from './pages/candidato/Progreso.jsx'
import EntrevistaVoz from './pages/candidato/EntrevistaVoz.jsx'
import SesionExpirada from './pages/candidato/SesionExpirada.jsx'

// Admin
import Dashboard from './pages/admin/Dashboard.jsx'
import Vacantes from './pages/admin/Vacantes.jsx'
import VacanteForm from './pages/admin/VacanteForm.jsx'
import VacanteDetalle from './pages/admin/VacanteDetalle.jsx'
import Candidatos from './pages/admin/Candidatos.jsx'
import CandidatoRegistrar from './pages/admin/CandidatoRegistrar.jsx'
import CandidatoDetalle from './pages/admin/CandidatoDetalle.jsx'
import Ranking from './pages/admin/Ranking.jsx'
import BancoTalento from './pages/admin/BancoTalento.jsx'
import Examenes from './pages/admin/Examenes.jsx'
import ExamenDetalle from './pages/admin/ExamenDetalle.jsx'
import EntrevistasIA from './pages/admin/EntrevistasIA.jsx'
import EntrevistaDetalle from './pages/admin/EntrevistaDetalle.jsx'
import Auditoria from './pages/admin/Auditoria.jsx'
import Plantillas from './pages/admin/Plantillas.jsx'
import Areas from './pages/admin/Areas.jsx'
import Usuarios from './pages/admin/Usuarios.jsx'

// En desarrollo se permite entrar sin backend; en producción exige token
function ProtectedRoute({ children }) {
  if (import.meta.env.DEV) return children
  const token = localStorage.getItem('vael_token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('vael_theme') || 'light')

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('vael_theme', theme)
  }, [theme])

  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Postulación pública */}
      <Route element={<CandidatoLayout />}>
        <Route path="/postular/:codigo" element={<Postular />} />
      </Route>

      {/* Portal del candidato */}
      <Route path="/candidato" element={<CandidatoLayout />}>
        <Route index element={<RedireccionadorCandidato />} />
        <Route path="acceso" element={<Acceso />} />
        <Route path="instrucciones" element={<ExamenInstrucciones />} />
        <Route path="examen" element={<Examen />} />
        <Route path="finalizado" element={<ExamenFinalizado />} />
        <Route path="progreso" element={<Progreso />} />
        <Route path="entrevista" element={<EntrevistaVoz />} />
        <Route path="expirado" element={<SesionExpirada />} />
      </Route>

      {/* Panel admin */}
      <Route path="/" element={
        <ProtectedRoute>
          <AdminLayout theme={theme} setTheme={setTheme} />
        </ProtectedRoute>
      }>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />

        <Route path="vacantes" element={<Vacantes />} />
        <Route path="vacantes/nueva" element={<VacanteForm />} />
        <Route path="vacantes/:id" element={<VacanteDetalle />} />
        <Route path="vacantes/:id/editar" element={<VacanteForm />} />

        <Route path="candidatos" element={<Candidatos />} />
        <Route path="candidatos/registrar" element={<CandidatoRegistrar />} />
        <Route path="candidatos/:id" element={<CandidatoDetalle />} />

        <Route path="ranking" element={<Ranking />} />
        <Route path="banco-talento" element={<BancoTalento />} />

        <Route path="examenes" element={<Examenes />} />
        <Route path="examenes/:id" element={<ExamenDetalle />} />

        <Route path="entrevistas" element={<EntrevistasIA />} />
        <Route path="entrevistas/:id" element={<EntrevistaDetalle />} />

        <Route path="auditoria" element={<Auditoria />} />
        <Route path="plantillas" element={<Plantillas />} />
        <Route path="areas" element={<Areas />} />
        <Route path="usuarios" element={<Usuarios />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}