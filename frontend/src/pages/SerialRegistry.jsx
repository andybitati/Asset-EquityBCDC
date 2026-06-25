import { useMemo, useState } from 'react'
import { normalizeBusinessText } from '../utils/text'

function matches(item, query) {
  if (!query) return true
  return [
    item.id,
    item.equipment_type,
    item.serial_number,
    item.status,
    item.entry_movement_id,
    item.exit_movement_id,
  ].filter(value => value !== null && value !== undefined)
    .some(value => String(value).toLowerCase().includes(query))
}

export default function SerialRegistryPage({ serialRegistry = { items: [], counts: {} }, searchTerm = '' }) {
  const [status, setStatus] = useState('all')
  const [localQuery, setLocalQuery] = useState('')
  const normalizedQuery = (localQuery || searchTerm).trim().toLowerCase()
  const items = serialRegistry.items || []
  const filtered = useMemo(() => items
    .filter(item => status === 'all' || item.status === status)
    .filter(item => matches(item, normalizedQuery)), [items, status, normalizedQuery])

  return (
    <div className="page serial-registry-page">
      <div className="page-header">
        <h2>Registre des numéros de série</h2>
        <div className="segmented-control">
          <button type="button" className={status === 'all' ? 'active' : ''} onClick={() => setStatus('all')}>Tous</button>
          <button type="button" className={status === 'in_stock' ? 'active' : ''} onClick={() => setStatus('in_stock')}>En stock</button>
          <button type="button" className={status === 'exited' ? 'active' : ''} onClick={() => setStatus('exited')}>Sortis</button>
        </div>
      </div>
      <div className="panel compact-toolbar">
        <input
          value={localQuery}
          onChange={event => setLocalQuery(event.target.value)}
          placeholder="Filtrer par série, type, statut ou ID..."
        />
      </div>

      <div className="kpi-grid compact-kpis">
        <div className="kpi-card">
          <span>Total séries</span>
          <strong>{serialRegistry.counts?.total || items.length}</strong>
          <small>Unités traçables</small>
        </div>
        <div className="kpi-card">
          <span>Disponibles</span>
          <strong>{serialRegistry.counts?.in_stock || 0}</strong>
          <small>Sortie possible</small>
        </div>
        <div className="kpi-card">
          <span>Sorties</span>
          <strong>{serialRegistry.counts?.exited || 0}</strong>
          <small>Rattachées à un mouvement</small>
        </div>
      </div>

      <div className="panel table-panel">
        <div className="panel-heading">
          <h3>Séries enregistrées</h3>
          <span>{filtered.length} ligne(s)</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>ID série</th>
                <th>Statut</th>
                <th>Type</th>
                <th>Numéro de série</th>
                <th>Entrée</th>
                <th>Sortie</th>
                <th>Dernière mise à jour</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(item => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td><span className={`status-pill ${item.status}`}>{item.status === 'in_stock' ? 'En stock' : 'Sorti'}</span></td>
                  <td>{item.equipment_type}</td>
                  <td>{normalizeBusinessText(item.serial_number)}</td>
                  <td>{item.entry_movement_id || '-'}</td>
                  <td>{item.exit_movement_id || '-'}</td>
                  <td>{item.updated_at ? new Date(item.updated_at).toLocaleString() : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
