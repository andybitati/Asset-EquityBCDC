import { useCallback, useEffect, useState } from 'react'
import LoginPage from './pages/Login'
import DashboardPage from './pages/Dashboard'
import InventoryPage from './pages/Inventory'
import MovementsPage from './pages/Movements'
import ExportPage from './pages/Export'
import ProfilePage from './pages/Profile'
import AuditPage from './pages/Audit'
import NavBar from './components/NavBar'
import { fetchCurrentUser, fetchInventory, fetchStockItems, fetchForecast, fetchMovements, logoutRequest } from './services/api'

const pages = {
  dashboard: DashboardPage,
  inventory: InventoryPage,
  movements: MovementsPage,
  export: ExportPage,
  profile: ProfilePage,
  audit: AuditPage,
}

export default function App() {
  const [token, setToken] = useState(null)
  const [page, setPage] = useState('dashboard')
  const [inventory, setInventory] = useState({})
  const [stockItems, setStockItems] = useState([])
  const [forecast, setForecast] = useState(null)
  const [movements, setMovements] = useState([])
  const [user, setUser] = useState(null)
  const [searchInput, setSearchInput] = useState('')
  const [dashboardSearch, setDashboardSearch] = useState('')

  const refreshData = useCallback(() => {
    if (!token) return
    fetchCurrentUser(token).then(data => setUser(data.user || null))
    fetchInventory(token).then(data => setInventory(data.inventory || {}))
    fetchStockItems(token).then(data => setStockItems(data.items || []))
    fetchForecast(token).then(setForecast)
    fetchMovements(token).then(data => setMovements(data.movements || []))
  }, [token])

  useEffect(() => {
    refreshData()
  }, [refreshData])

  useEffect(() => {
    if (!token) return undefined
    const timer = window.setInterval(refreshData, 15000)
    return () => window.clearInterval(timer)
  }, [refreshData, token])

  useEffect(() => {
    if (!token) return
    const wsHost = ['48621', '5173'].includes(window.location.port) ? '127.0.0.1:48620' : window.location.host
    const wsUrl = import.meta.env.VITE_WS_URL || `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${wsHost}/ws/updates`
    const ws = new WebSocket(wsUrl)
    ws.onopen = () => console.log('WebSocket connecté')
    ws.onmessage = event => {
      const payload = JSON.parse(event.data)
      if (payload.inventory) {
        setInventory(payload.inventory)
      }
      if (payload.forecast) {
        setForecast(payload.forecast)
      }
      if (payload.stock_items) {
        setStockItems(payload.stock_items)
      }
      if (payload.movements) {
        setMovements(payload.movements)
      }
    }
    ws.onclose = () => console.log('WebSocket déconnecté')
    return () => ws.close()
  }, [token])

  if (!token) {
    return <LoginPage onLogin={setToken} />
  }

  const handleLogout = async () => {
    try {
      await logoutRequest(token)
    } catch (e) {
      // ignore errors
    }
    setToken(null)
    setUser(null)
  }

  const runSearch = () => {
    setDashboardSearch(searchInput.trim())
    setPage('dashboard')
  }

  const handleSearchChange = event => {
    const value = event.target.value
    setSearchInput(value)
    setDashboardSearch(value.trim())
    if (value.trim()) {
      setPage('dashboard')
    }
  }

  const CurrentPage = pages[page] || DashboardPage
  return (
    <div className="app-shell">
      <NavBar active={page} user={user} onNavigate={setPage} onLogout={handleLogout} />
      <main className="content">
        <div className="app-topbar">
          <div>
            <span className="eyebrow">Assets Equity BCDC</span>
            <h2>Gestion du stock informatique</h2>
          </div>
          <div className="dashboard-actions">
            <div className="search-group">
              <input
                className="search-input"
                value={searchInput}
                onChange={handleSearchChange}
                onKeyDown={event => {
                  if (event.key === 'Enter') runSearch()
                }}
                placeholder="Rechercher type, modèle, série..."
              />
              <button type="button" onClick={runSearch}>Rechercher</button>
            </div>
            {user && (
              <div className="dashboard-user">
                <img src={user.photo_url || '/avatar-user-red.svg'} alt={user.display_name} />
                <div>
                  <strong>{user.display_name || user.username}</strong>
                  <span>{user.role || user.username}</span>
                </div>
              </div>
            )}
            <button type="button" onClick={refreshData}>Actualiser</button>
          </div>
        </div>
        <CurrentPage
          token={token}
          inventory={inventory}
          stockItems={stockItems}
          forecast={forecast}
          movements={movements}
          user={user}
          refresh={refreshData}
          searchTerm={dashboardSearch}
        />
      </main>
    </div>
  )
}
