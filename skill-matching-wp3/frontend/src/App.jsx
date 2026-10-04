import { useState } from 'react'
import heroImg from './assets/hero.png'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import { Navigate, Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar.jsx'
import Profil from './pages/Profil.jsx'
import Offres from './pages/Offres.jsx'
import DetailOffre from './pages/DetailOffre.jsx'
import Roadmap from './pages/Roadmap.jsx'

function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Navigate to="/profil" replace />} />
          <Route path="/profil" element={<Profil />} />
          <Route path="/offres" element={<Offres />} />
          <Route path="/offres/:offreId" element={<DetailOffre />} />
          <Route path="/roadmap/:offreId" element={<Roadmap />} />
          <Route path="*" element={<Navigate to="/profil" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
