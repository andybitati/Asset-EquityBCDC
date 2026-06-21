import { useState } from 'react'

export default function ExportPage({ token }) {
  const [status, setStatus] = useState(null)

  const downloadCsv = async () => {
    setStatus(null)
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
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
    </div>
  )
}
