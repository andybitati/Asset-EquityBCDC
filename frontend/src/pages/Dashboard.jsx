import { useMemo, useState } from 'react'
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'

const chartColors = ['#b60f1e', '#f5a400', '#2563eb', '#059669', '#7c3aed', '#0891b2', '#ea580c', '#4b5563']

function formatDate(value) {
  return new Date(value).toLocaleDateString()
}

function buildHistory(movements) {
  const sorted = [...movements].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
  const totals = {}
  const byDate = new Map()

  sorted.forEach(record => {
    const type = record.equipment_type
    totals[type] = totals[type] || 0
    totals[type] += record.movement_type === 'Entrée' ? record.quantity : -record.quantity
    byDate.set(formatDate(record.timestamp), { ...(byDate.get(formatDate(record.timestamp)) || {}), ...totals })
  })

  return Array.from(byDate.entries()).map(([date, values]) => ({ date, ...values }))
}

export default function DashboardPage({ inventory, stockItems = [], movements = [], forecast, user, refresh }) {
  const [query, setQuery] = useState('')
  const chartData = Object.entries(inventory).map(([name, value]) => ({ name, value }))
  const totalStock = chartData.reduce((sum, item) => sum + item.value, 0)
  const totalEntries = movements.filter(item => item.movement_type === 'Entrée').reduce((sum, item) => sum + item.quantity, 0)
  const totalExits = movements.filter(item => item.movement_type === 'Sortie').reduce((sum, item) => sum + item.quantity, 0)
  const activeTypes = chartData.filter(item => item.value > 0).length
  const history = useMemo(() => buildHistory(movements), [movements])
  const risks = [...(forecast?.risks || [])]
    .sort((a, b) => Number(b.exits_locked) - Number(a.exits_locked) || a.current_stock - b.current_stock)
    .slice(0, 4)
  const normalizedQuery = query.trim().toLowerCase()
  const filteredMovements = movements.filter(record => {
    if (!normalizedQuery) return true
    return [
      record.equipment_type,
      record.serial_number,
      record.model,
      record.destination,
      record.taken_by,
      record.initiated_by,
      record.notes,
      record.movement_type,
    ].filter(Boolean).some(value => String(value).toLowerCase().includes(normalizedQuery))
  }).slice(-8).reverse()

  return (
    <div className="page dashboard-page">
      <div className="dashboard-topbar">
        <div>
          <span className="eyebrow">Assets Equity BCDC</span>
          <h2>Gestion du stock informatique</h2>
        </div>
        <div className="dashboard-actions">
          <input
            className="search-input"
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder="Rechercher type, modèle, série..."
          />
          {user && (
            <div className="dashboard-user">
              <img src={user.photo_url} alt={user.display_name} />
              <div>
                <strong>{user.display_name || user.username}</strong>
                <span>{user.role || user.username}</span>
              </div>
            </div>
          )}
          <button onClick={refresh}>Actualiser</button>
        </div>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card">
          <span>Stock total</span>
          <strong>{totalStock}</strong>
          <small>Unités au dépôt</small>
        </div>
        <div className="kpi-card">
          <span>Entrées</span>
          <strong>{totalEntries}</strong>
          <small>Depuis le démarrage du suivi</small>
        </div>
        <div className="kpi-card">
          <span>Sorties</span>
          <strong>{totalExits}</strong>
          <small>Mouvements validés</small>
        </div>
        <div className="kpi-card">
          <span>Types actifs</span>
          <strong>{activeTypes}</strong>
          <small>Catégories en stock</small>
        </div>
      </div>

      <div className="dashboard-layout">
        <div className="panel chart-panel">
          <div className="panel-heading">
            <h3>Évolution du stock</h3>
            <span>Par type de matériel</span>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={history} margin={{ top: 10, right: 24, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="date" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              {chartData.map((item, index) => (
                <Line
                  key={item.name}
                  type="monotone"
                  dataKey={item.name}
                  stroke={chartColors[index % chartColors.length]}
                  strokeWidth={3}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <h3>Prévision pénurie</h3>
            <span>{forecast?.recommendation || 'En attente de données'}</span>
          </div>
          <div className="risk-list">
            {risks.map(item => (
              <div
                key={item.equipment_type}
                className={`risk-item ${item.exits_locked || item.current_stock <= item.reorder_threshold ? 'risk-alert' : ''}`}
              >
                <div>
                  <strong>
                    {item.equipment_type}
                    {(item.exits_locked || item.current_stock <= item.reorder_threshold) && (
                      <span className="alert-badge">Commander</span>
                    )}
                  </strong>
                  <span>{item.recommendation}</span>
                  <span>Commande: {item.reorder_threshold} | Réserve: {item.emergency_reserve_threshold}</span>
                </div>
                <div>
                  <strong>{item.current_stock}</strong>
                  <span>{item.exits_locked ? 'Sorties bloquées' : item.estimated_days_to_empty ? `${item.estimated_days_to_empty} j` : 'N/A'}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <h3>Stock par catégorie</h3>
            <span>Quantités disponibles</span>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="name" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#b60f1e" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <h3>Suivi recherché</h3>
            <span>{filteredMovements.length} mouvement(s)</span>
          </div>
          <div className="movement-feed">
            {filteredMovements.length ? filteredMovements.map(record => (
              <div key={record.id} className="movement-item">
                <div>
                  <strong>{record.equipment_type}</strong>
                  <span>{record.serial_number || '-'} / {record.model || '-'}</span>
                  <span>{record.destination || '-'} {record.taken_by ? `- ${record.taken_by}` : ''}</span>
                  <span>Initié par: {record.initiated_by || '-'}</span>
                </div>
                <div>
                  <strong className={record.movement_type === 'Entrée' ? 'positive' : 'negative'}>
                    {record.movement_type === 'Entrée' ? '+' : '-'}{record.quantity}
                  </strong>
                  <span>{formatDate(record.timestamp)}</span>
                </div>
              </div>
            )) : (
              <div className="empty-state">Aucun mouvement ne correspond à la recherche.</div>
            )}
          </div>
        </div>
      </div>

      <div className="panel table-panel">
        <div className="panel-heading">
          <h3>Matériels disponibles</h3>
          <span>{stockItems.length} élément(s) traçables</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Série</th>
              <th>Modèle</th>
              <th>Quantité</th>
            </tr>
          </thead>
          <tbody>
            {stockItems.map(item => (
              <tr key={item.material_id}>
                <td>{item.equipment_type}</td>
                <td>{item.serial_number || '-'}</td>
                <td>{item.model || '-'}</td>
                <td>{item.quantity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
