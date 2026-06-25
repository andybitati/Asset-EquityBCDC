import { useMemo, useState } from 'react'
import { updateStockPolicy } from '../services/api'

const numericFields = [
  { key: 'lead_time_days', label: 'Délai fournisseur', suffix: 'j' },
  { key: 'emergency_days', label: 'Réserve urgence', suffix: 'j' },
  { key: 'minimum_stock', label: 'Minimum absolu', suffix: 'u' },
  { key: 'target_days', label: 'Couverture cible', suffix: 'j' },
  { key: 'service_factor', label: 'Facteur service', suffix: 'σ' },
]

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function matchesPolicy(policy, query) {
  if (!query) return true
  return policy.equipment_type.toLowerCase().includes(query)
}

export default function StockPoliciesPage({ token, stockPolicies = [], forecast, user, refresh, searchTerm = '' }) {
  const canEdit = user?.role === 'admin' || user?.role === 'manager'
  const [localQuery, setLocalQuery] = useState('')
  const [drafts, setDrafts] = useState({})
  const [saving, setSaving] = useState(null)
  const [message, setMessage] = useState(null)
  const normalizedQuery = (localQuery || searchTerm).trim().toLowerCase()
  const riskByType = useMemo(() => new Map((forecast?.risks || []).map(item => [item.equipment_type, item])), [forecast])
  const policies = useMemo(() => [...stockPolicies]
    .filter(policy => matchesPolicy(policy, normalizedQuery))
    .sort((a, b) => a.equipment_type.localeCompare(b.equipment_type)), [stockPolicies, normalizedQuery])

  const getDraft = policy => drafts[policy.equipment_type] || policy

  const changeField = (policy, key, value) => {
    setDrafts(previous => ({
      ...previous,
      [policy.equipment_type]: {
        ...getDraft(policy),
        [key]: value,
      },
    }))
  }

  const savePolicy = async policy => {
    const draft = getDraft(policy)
    const payload = {
      lead_time_days: Number(draft.lead_time_days),
      emergency_days: Number(draft.emergency_days),
      minimum_stock: Number(draft.minimum_stock),
      target_days: Number(draft.target_days),
      service_factor: Number(draft.service_factor),
    }
    setSaving(policy.equipment_type)
    setMessage(null)
    try {
      await updateStockPolicy(token, policy.equipment_type, payload)
      setDrafts(previous => {
        const next = { ...previous }
        delete next[policy.equipment_type]
        return next
      })
      setMessage({ type: 'success', text: `Politique mise à jour pour ${policy.equipment_type}.` })
      await refresh()
    } catch (error) {
      setMessage({ type: 'error', text: error.message })
    } finally {
      setSaving(null)
    }
  }

  return (
    <div className="page stock-policies-page">
      <div className="page-header">
        <div>
          <h2>Politiques de stock</h2>
          <p className="page-subtitle">Hypothèses utilisées pour calculer commande, réserve d'urgence, stock de sécurité et cible.</p>
        </div>
      </div>

      <div className="policy-method panel">
        <div>
          <strong>Formule active</strong>
          <span>Commande = demande moyenne × délai + facteur service × écart-type × √délai.</span>
        </div>
        <div>
          <strong>Sorties</strong>
          <span>Jamais bloquées par seuil : l'application demande l'avis du responsable et trace l'opération.</span>
        </div>
      </div>

      <div className="panel compact-toolbar">
        <input
          value={localQuery}
          onChange={event => setLocalQuery(event.target.value)}
          placeholder="Filtrer par type de matériel..."
        />
      </div>

      {message && (
        <div className={message.type === 'error' ? 'error-message' : 'success-message'}>
          {message.text}
        </div>
      )}

      <div className="panel table-panel">
        <div className="panel-heading">
          <h3>Paramètres par type</h3>
          <span>{canEdit ? 'Modifiable par admin/manager' : 'Lecture seule'}</span>
        </div>
        <div className="table-scroll">
          <table className="policy-table">
            <thead>
              <tr>
                <th>Type</th>
                {numericFields.map(field => <th key={field.key}>{field.label}</th>)}
                <th>Seuils calculés</th>
                <th>MAJ</th>
                {canEdit && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {policies.map(policy => {
                const draft = getDraft(policy)
                const risk = riskByType.get(policy.equipment_type)
                return (
                  <tr key={policy.equipment_type}>
                    <td><strong>{policy.equipment_type}</strong></td>
                    {numericFields.map(field => (
                      <td key={field.key}>
                        {canEdit ? (
                          <label className="inline-number">
                            <input
                              type="number"
                              min={field.key === 'service_factor' ? '0' : '0'}
                              step={field.key === 'service_factor' ? '0.01' : '1'}
                              value={draft[field.key]}
                              onChange={event => changeField(policy, field.key, event.target.value)}
                            />
                            <span>{field.suffix}</span>
                          </label>
                        ) : (
                          <span>{policy[field.key]} {field.suffix}</span>
                        )}
                      </td>
                    ))}
                    <td>
                      {risk ? (
                        <div className="threshold-stack">
                          <span>Commande {risk.reorder_threshold}</span>
                          <span>Réserve {risk.emergency_reserve_threshold}</span>
                          <span>Cible {risk.target_stock}</span>
                        </div>
                      ) : '-'}
                    </td>
                    <td>{formatDate(policy.updated_at)}</td>
                    {canEdit && (
                      <td>
                        <button
                          type="button"
                          className="small-action"
                          disabled={saving === policy.equipment_type}
                          onClick={() => savePolicy(policy)}
                        >
                          {saving === policy.equipment_type ? '...' : 'Valider'}
                        </button>
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
