import { useState } from 'react'
import { normalizeBusinessText } from '../utils/text'

const csvColumns = [
  { key: 'id', label: 'id' },
  { key: 'material_id', label: 'material_id' },
  { key: 'timestamp', label: 'timestamp' },
  { key: 'movement_type', label: 'movement_type' },
  { key: 'equipment_type', label: 'equipment_type' },
  { key: 'quantity', label: 'quantity' },
  { key: 'serial_number', label: 'serial_number' },
  { key: 'model', label: 'model' },
  { key: 'destination', label: 'destination' },
  { key: 'taken_by', label: 'taken_by' },
  { key: 'initiated_by', label: 'initiated_by' },
  { key: 'notes', label: 'notes' },
]

function csvValue(record, key) {
  if (key === 'timestamp' && record.timestamp) {
    return new Date(record.timestamp).toISOString()
  }
  return normalizeBusinessText(record[key] ?? '')
}

export default function ExportPage({ token, movements = [] }) {
  const [status, setStatus] = useState(null)
  const previewRows = [...movements].slice(-8).reverse()

  const downloadCsv = async () => {
    setStatus(null)
    try {
      const isViteDevServer = ['48621', '5173'].includes(window.location.port)
      const apiUrl = import.meta.env.VITE_API_URL || (isViteDevServer ? 'http://127.0.0.1:48620' : window.location.origin)
      const response = await fetch(`${apiUrl}/exports/movements.csv`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (!response.ok) {
        throw new Error('Fichier introuvable')
      }
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'movements.csv'
      link.click()
      URL.revokeObjectURL(url)
      setStatus('Export CSV téléchargé')
    } catch (err) {
      setStatus('Erreur lors de l’export CSV')
    }
  }

  return (
    <div className="page export-page">
      <div className="page-header">
        <h2>Export CSV</h2>
      </div>
      <div className="panel export-panel">
        <p>Les mouvements sont enregistrés automatiquement et peuvent être exportés.</p>
        <button onClick={downloadCsv}>Télécharger le fichier CSV</button>
        {status && <div className="info-message">{status}</div>}
      </div>

      <div className="panel table-panel csv-preview-panel">
        <div className="panel-heading">
          <div>
            <h3>Aperçu de la feuille CSV</h3>
            <span>Les colonnes ci-dessous seront organisées dans cet ordre. Le fichier utilise le séparateur ; pour Excel.</span>
          </div>
          <span>{movements.length} mouvement(s) exportable(s)</span>
        </div>

        <div className="csv-structure">
          {csvColumns.map((column, index) => (
            <div key={column.key}>
              <strong>{index + 1}</strong>
              <span>{column.label}</span>
            </div>
          ))}
        </div>

        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {csvColumns.map(column => (
                  <th key={column.key}>{column.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {previewRows.length ? previewRows.map(record => (
                <tr key={record.id}>
                  {csvColumns.map(column => (
                    <td key={column.key}>{csvValue(record, column.key) || '-'}</td>
                  ))}
                </tr>
              )) : (
                <tr>
                  <td colSpan={csvColumns.length}>Aucun mouvement à prévisualiser pour le moment.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="form-hint">Aperçu limité aux 8 mouvements les plus récents. Le fichier CSV exporte l’ensemble des mouvements disponibles.</p>
      </div>
    </div>
  )
}
