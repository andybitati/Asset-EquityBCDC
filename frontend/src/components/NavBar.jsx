export default function NavBar({ active, onNavigate }) {
  return (
    <nav className="sidebar">
      <div className="brand">
        <div className="brand-logo">E</div>
        <div className="brand-text">
          <span className="brand-title">Equity</span>
          <span className="brand-subtitle">BCDC</span>
        </div>
      </div>
      <button className={active === 'dashboard' ? 'active' : ''} onClick={() => onNavigate('dashboard')}>Tableau de bord</button>
      <button className={active === 'inventory' ? 'active' : ''} onClick={() => onNavigate('inventory')}>Entrées / Sorties</button>
      <button className={active === 'movements' ? 'active' : ''} onClick={() => onNavigate('movements')}>Historique</button>
      <button className={active === 'export' ? 'active' : ''} onClick={() => onNavigate('export')}>Export CSV</button>
    </nav>
  )
}
