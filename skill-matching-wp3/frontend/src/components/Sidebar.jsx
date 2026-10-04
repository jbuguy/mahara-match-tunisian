import { NavLink } from 'react-router-dom'

const liens = [
  { to: '/profil', label: 'Mon profil', icon: '01' },
  { to: '/offres', label: 'Offres recommandées', icon: '02' },
]

function Sidebar() {
  return (
    <aside className="sidebar">
      <NavLink className="brand" to="/profil" aria-label="Mahara Match, accueil candidat">
        <span className="brand-mark">M</span>
        <span><strong>Mahara Match</strong><small>Espace candidat</small></span>
      </NavLink>
      <nav className="side-nav" aria-label="Navigation principale">
        {liens.map((lien) => (
          <NavLink key={lien.to} to={lien.to} className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            <span className="nav-index">{lien.icon}</span>{lien.label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-note"><span className="status-dot" />Moteur de compétences<br /><small>WP3 · Tunisie</small></div>
    </aside>
  )
}

export default Sidebar