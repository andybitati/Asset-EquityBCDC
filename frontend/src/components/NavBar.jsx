export default function NavBar({ active, user, onNavigate, onLogout }) {
  return (
    <nav className="sidebar">
      <div className="brand">
        <div className="brand-logo-frame">
          <img className="brand-logo-img" src="/equity-bank-logo.png" alt="Equity Logo" />
        </div>
        <div className="brand-text">
          <span className="brand-title">Assets</span>
          <span className="brand-subtitle">Equity BCDC</span>
        </div>
      </div>
      {user && (
        <div className="user-profile">
          <img className="user-avatar" src={user.photo_url} alt={user.display_name} />
          <div className="user-info">
            <strong>{user.display_name}</strong>
            <span>{user.username}</span>
          </div>
        </div>
      )}
      <button className={active === 'dashboard' ? 'active' : ''} onClick={() => onNavigate('dashboard')}>Dashboard</button>
      <button className={active === 'inventory' ? 'active' : ''} onClick={() => onNavigate('inventory')}>Stock</button>
      <button className={active === 'movements' ? 'active' : ''} onClick={() => onNavigate('movements')}>Mouvements</button>
      <button className={active === 'export' ? 'active' : ''} onClick={() => onNavigate('export')}>Export CSV</button>
      {(user?.role === 'admin' || user?.role === 'auditor') && (
        <button className={active === 'audit' ? 'active' : ''} onClick={() => onNavigate('audit')}>Audit</button>
      )}
      <button className={active === 'profile' ? 'active' : ''} onClick={() => onNavigate('profile')}>Profil</button>
      <div style={{ marginTop: 'auto' }}>
        <button className="logout-button" onClick={() => onLogout && onLogout()}>Déconnexion</button>
      </div>
    </nav>
  )
}
