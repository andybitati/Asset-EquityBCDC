import { useEffect, useState } from 'react'
import LoginPage from './pages/Login'
import DashboardPage from './pages/Dashboard'
import InventoryPage from './pages/Inventory'
import MovementsPage from './pages/Movements'
import ExportPage from './pages/Export'
import NavBar from './components/NavBar'
import { fetchInventory, fetchForecast, fetchMovements } from './services/api'

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

  useEffect(() => {
    if (!token) return
    fetchInventory(token).then(data => setInventory(data.inventory || {}))
    fetchForecast(token).then(setForecast)
    fetchMovements(token).then(data => setMovements(data.movements || []))
  }, [token])

  useEffect(() => {
    if (!token) return
    const ws = new WebSocket('ws://127.0.0.1:8000/ws/updates')
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

  const CurrentPage = pages[page] || DashboardPage
  return (
    <div className="app-shell">
      <NavBar active={page} onNavigate={setPage} />
      <main className="content">
        <CurrentPage
          token={token}
          inventory={inventory}
          forecast={forecast}
          movements={movements}
          refresh={() => {
            fetchInventory(token).then(data => setInventory(data.inventory || {}))
            fetchForecast(token).then(setForecast)
            fetchMovements(token).then(data => setMovements(data.movements || []))
          }}
        />
      </main>
    </div>
  )
}
