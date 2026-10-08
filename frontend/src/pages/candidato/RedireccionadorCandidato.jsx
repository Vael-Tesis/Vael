import { Navigate } from 'react-router-dom'

// /candidato → lleva al progreso si ya hay sesión, o al acceso si no
export default function RedireccionadorCandidato() {
  const tieneSesion = !!sessionStorage.getItem('vael_candidate_token')
  return <Navigate to={tieneSesion ? '/candidato/progreso' : '/candidato/acceso'} replace />
}