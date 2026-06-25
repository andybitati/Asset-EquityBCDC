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

function riskLevel(item) {
  if (item.current_stock <= 0) return 'rupture'
  if (item.manager_review_required) return 'critical'
  if (item.current_stock <= item.reorder_threshold) return 'warning'
  return 'ok'
}

function riskLabel(level) {
  return {
    rupture: 'Rupture',
    critical: 'Avis responsable',
    warning: 'Commander',
    ok: 'OK',
  }[level]
}

export default function DashboardPage({ inventory, stockItems = [], serialRegistry = { items: [], counts: {} }, movements = [], forecast, searchTerm = '' }) {
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
  const knownTypes = new Set([
    ...Object.entries(displayInventory).filter(([, value]) => value !== 0).map(([type]) => type),
    ...filteredMovementsForStats.map(record => record.equipment_type),
  ])
  const topChartTypes = [...chartData]
    .filter(item => item.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
  const trackedSerials = serialRegistry.counts || {}
  const risks = [...(forecast?.risks || [])]
    .filter(item => !normalizedQuery || item.equipment_type.toLowerCase().includes(normalizedQuery))
    .filter(item => knownTypes.has(item.equipment_type))
    .map(item => ({ ...item, level: riskLevel(item) }))
    .filter(item => item.level !== 'ok')
    .sort((a, b) => {
      const rank = { rupture: 0, critical: 1, warning: 2, ok: 3 }
      return rank[a.level] - rank[b.level] || a.current_stock - b.current_stock
    })
    .slice(0, 6)
  const knownRisks = (forecast?.risks || []).filter(item => knownTypes.has(item.equipment_type))
  const ruptureCount = knownRisks.filter(item => riskLevel(item) === 'rupture').length
  const criticalCount = knownRisks.filter(item => ['critical', 'warning'].includes(riskLevel(item))).length
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
          <span>Séries disponibles</span>
          <strong>{trackedSerials.in_stock || 0}</strong>
          <small>{trackedSerials.exited || 0} sorties tracées</small>
        </div>
        <div className="kpi-card">
          <span>Alertes stock</span>
          <strong>{criticalCount}</strong>
          <small>{ruptureCount} rupture(s), {activeTypes} type(s) actifs</small>
        </div>
      </div>

      <div className="dashboard-layout">
        <div className="panel chart-panel">
          <div className="panel-heading">
            <h3>Évolution du stock</h3>
            <span>Top {topChartTypes.length} types actifs</span>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={history} margin={{ top: 10, right: 24, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="date" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              {topChartTypes.map((item, index) => (
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
          <div className="chart-legend">
            {topChartTypes.map((item, index) => (
              <span key={item.name}><i style={{ background: chartColors[index % chartColors.length] }} />{item.name}</span>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <h3>Prévision pénurie</h3>
            <span>{risks.length ? `${risks.length} alerte(s) actionnable(s)` : 'Aucune alerte active'}</span>
          </div>
          <div className="risk-list">
            {risks.length ? risks.map(item => (
              <div
                key={item.equipment_type}
                className={`risk-item risk-${item.level}`}
              >
                <div>
                  <strong>
                    {item.equipment_type}
                    <span className="alert-badge">{riskLabel(item.level)}</span>
                  </strong>
                  <span>{item.recommendation}</span>
                  <span>Commande: {item.reorder_threshold} | Réserve: {item.emergency_reserve_threshold} | Cible: {item.target_stock}</span>
                  <span>Délai: {item.lead_time_days} j | Sécurité: {item.safety_stock} | Écart-type: {item.demand_std_dev}/j</span>
                </div>
                <div>
                  <strong>{item.current_stock}</strong>
                  <span>{item.manager_review_required ? 'Avis requis' : item.estimated_days_to_empty ? `${item.estimated_days_to_empty} j` : 'N/A'}</span>
                </div>
              </div>
            )) : (
              <div className="empty-state">Stock au-dessus des seuils opérationnels.</div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <h3>Stock par catégorie</h3>
            <span>Top disponibilités</span>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={[...chartData].filter(item => item.value > 0).sort((a, b) => b.value - a.value).slice(0, 10)} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
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
