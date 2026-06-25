import { useEffect, useState } from 'react'
import { fetchAuditLogs } from '../services/api'

function severityForAction(action) {
  if (['unknown_serial_exit_attempt', 'login_failure', 'admin_delete_user'].includes(action)) return 'high'
  if (['import_entry_serial_numbers', 'create_exit', 'admin_update_user'].includes(action)) return 'medium'
  return 'normal'
}

export default function AuditPage({ token }) {
  const [logs, setLogs] = useState([])
  const [status, setStatus] = useState('Chargement...')

  useEffect(() => {
    fetchAuditLogs(token)
      .then(data => {
        setLogs(data.audit_logs || [])
        setStatus(null)
      })
      .catch(() => setStatus("Impossible de charger les logs d'audit."))
  }, [token])

  return (
    <div className="page audit-page">
      <div className="page-header">
        <h2>Audit sécurité</h2>
      </div>
      <div className="panel table-panel">
        {status && <div className="info-message">{status}</div>}
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Utilisateur</th>
              <th>Action</th>
              <th>Entité</th>
              <th>ID</th>
              <th>Gravité</th>
              <th>IP</th>
              <th>Détails</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log, index) => (
              <tr key={`${log.created_at}-${index}`}>
                <td>{new Date(log.created_at).toLocaleString()}</td>
                <td>{log.actor_username || '-'}</td>
                <td>{log.action}</td>
                <td>{log.entity_type}</td>
                <td>{log.entity_id || '-'}</td>
                <td><span className={`severity-pill ${severityForAction(log.action)}`}>{severityForAction(log.action)}</span></td>
                <td>{log.ip_address || '-'}</td>
                <td className="details-cell">{log.new_value || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
