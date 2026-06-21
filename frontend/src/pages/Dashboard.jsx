import { useMemo } from 'react'
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { normalizeBusinessText } from '../utils/text'

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

function matchesSearch(record, normalizedQuery) {
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
}

export default function DashboardPage({ inventory, stockItems = [], movements = [], forecast, searchTerm = '' }) {
  const normalizedQuery = searchTerm.trim().toLowerCase()
  const filteredStockItems = stockItems.filter(item => matchesSearch(item, normalizedQuery))
  const filteredMovementsForStats = movements.filter(record => matchesSearch(record, normalizedQuery))
  const displayInventory = normalizedQuery
    ? filteredStockItems.reduce((totals, item) => {
        totals[item.equipment_type] = (totals[item.equipment_type] || 0) + item.quantity
        return totals
      }, {})
    : inventory
  const chartData = Object.entries(displayInventory).map(([name, value]) => ({ name, value }))
  const totalStock = chartData.reduce((sum, item) => sum + item.value, 0)
  const totalEntries = filteredMovementsForStats.filter(item => item.movement_type === 'Entrée').reduce((sum, item) => sum + item.quantity, 0)
  const totalExits = filteredMovementsForStats.filter(item => item.movement_type === 'Sortie').reduce((sum, item) => sum + item.quantity, 0)
  const activeTypes = chartData.filter(item => item.value > 0).length
  const history = useMemo(() => buildHistory(filteredMovementsForStats), [filteredMovementsForStats])
  const risks = [...(forecast?.risks || [])]
    .filter(item => !normalizedQuery || item.equipment_type.toLowerCase().includes(normalizedQuery))
    .sort((a, b) => Number(b.exits_locked) - Number(a.exits_locked) || a.current_stock - b.current_stock)
    .slice(0, 4)
  const filteredMovements = filteredMovementsForStats.slice(-8).reverse()

  return (
    <div className="page dashboard-page">
      {normalizedQuery && (
        <div className="search-result-banner">
          Résultat de recherche pour <strong>{searchTerm}</strong>
        </div>
      )}

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
          <p className="chart-explanation">
            Cette courbe montre le stock net disponible dans le temps. Une entrée fait monter la courbe du type concerné,
            une sortie la fait descendre. Elle ne sépare donc pas les entrées et les sorties : elle affiche le résultat
            final après chaque mouvement.
          </p>
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
                  <span>{normalizeBusinessText(record.destination) || '-'} {record.taken_by ? `- ${record.taken_by}` : ''}</span>
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
          <span>{filteredStockItems.length} élément(s) traçables</span>
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
            {filteredStockItems.map(item => (
              <tr key={item.material_id}>
                <td>{item.equipment_type}</td>
                <td>{normalizeBusinessText(item.serial_number) || '-'}</td>
                <td>{normalizeBusinessText(item.model) || '-'}</td>
                <td>{item.quantity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
