export default function NavBar({ active, user, onNavigate, onLogout }) {
  return (
    <nav className="sidebar">
      <div className="brand">
        <div className="brand-logo-frame">
          <img className="brand-logo-img" src="/assets-equity-logo.png" alt="Assets Equity BCDC" />
        </div>
        <div className="brand-text">
          <span className="brand-title">Assets</span>
          <span className="brand-subtitle">Equity BCDC</span>
        </div>
      </div>
      {user && (
        <div className="user-profile">
          <img className="user-avatar" src={user.photo_url || '/avatar-user-red.svg'} alt={user.display_name} />
          <div className="user-info">
            <strong>{user.display_name}</strong>
            <span>{user.username}</span>
          </div>
        </div>
      )}
      <button className={active === 'dashboard' ? 'active' : ''} onClick={() => onNavigate('dashboard')}>Dashboard</button>
      <button className={active === 'inventory' ? 'active' : ''} onClick={() => onNavigate('inventory')}>Stock</button>
      <button className={active === 'serials' ? 'active' : ''} onClick={() => onNavigate('serials')}>Registre séries</button>
      <button className={active === 'policies' ? 'active' : ''} onClick={() => onNavigate('policies')}>Politiques stock</button>
      <button className={active === 'movements' ? 'active' : ''} onClick={() => onNavigate('movements')}>Mouvements</button>
      <button className={active === 'export' ? 'active' : ''} onClick={() => onNavigate('export')}>Export CSV</button>
      {(user?.role === 'admin' || user?.role === 'auditor') && (
        <button className={active === 'audit' ? 'active' : ''} onClick={() => onNavigate('audit')}>Audit</button>
      )}
      <button className={active === 'profile' ? 'active' : ''} onClick={() => onNavigate('profile')}>Profil</button>
      <div className="sidebar-logout">
        <button className="logout-button" onClick={() => onLogout && onLogout()}>Déconnexion</button>
      </div>
    </nav>
  )
}
