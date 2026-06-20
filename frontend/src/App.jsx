import { useEffect, useState } from 'react'
import LoginPage from './pages/Login'
import DashboardPage from './pages/Dashboard'
import InventoryPage from './pages/Inventory'
import MovementsPage from './pages/Movements'
import ExportPage from './pages/Export'
import NavBar from './components/NavBar'
import { fetchCurrentUser, fetchInventory, fetchForecast, fetchMovements, logoutRequest } from './services/api'

const pages = {
  dashboard: DashboardPage,
  inventory: InventoryPage,
  movements: MovementsPage,
  export: ExportPage,
}

export default function App() {
  const [token, setToken] = useState(null)
  const [page, setPage] = useState('dashboard')
  const [inventory, setInventory] = useState({})
  const [forecast, setForecast] = useState(null)
  const [movements, setMovements] = useState([])
  const [user, setUser] = useState(null)

  useEffect(() => {
    if (!token) return
    fetchCurrentUser(token).then(data => setUser(data.user || null))
    fetchInventory(token).then(data => setInventory(data.inventory || {}))
    fetchForecast(token).then(setForecast)
    fetchMovements(token).then(data => setMovements(data.movements || []))
  }, [token])

  useEffect(() => {
    if (!token) return
    const wsUrl = import.meta.env.VITE_WS_URL || `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:8000/ws/updates`
    const ws = new WebSocket(wsUrl)
    ws.onopen = () => console.log('WebSocket connecté')
    ws.onmessage = event => {
      const payload = JSON.parse(event.data)
      setInventory(payload.inventory)
      setForecast(payload.forecast)
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

  const CurrentPage = pages[page] || DashboardPage
  return (
    <div className="app-shell">
      <NavBar active={page} user={user} onNavigate={setPage} onLogout={handleLogout} />
      <main className="content">
        <CurrentPage
          token={token}
          inventory={inventory}
          forecast={forecast}
          movements={movements}
          refresh={() => {
            fetchCurrentUser(token).then(data => setUser(data.user || null))
            fetchInventory(token).then(data => setInventory(data.inventory || {}))
            fetchForecast(token).then(setForecast)
            fetchMovements(token).then(data => setMovements(data.movements || []))
          }}
        />
      </main>
    </div>
  )
}
