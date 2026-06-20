import { useState } from 'react'
import { submitEntry, submitExit } from '../services/api'

const defaultItem = {
  type: 'Desktop',
  quantity: 1,
  serial_number: '',
  model: '',
  destination: '',
  notes: '',
}

export default function InventoryPage({ token, refresh }) {
  const [item, setItem] = useState(defaultItem)
  const [message, setMessage] = useState(null)

  const handleSubmit = async (endpoint, label) => {
    setMessage(null)
    try {
      const payload = {
        type: item.type,
        quantity: Number(item.quantity),
        serial_number: item.serial_number,
        model: item.model,
        destination: item.destination,
        notes: item.notes,
      }
      const result = endpoint(token, payload)
      await result
      setMessage(`${label} enregistré avec succès`)
      setItem(defaultItem)
      refresh()
    } catch (err) {
      setMessage('Erreur de sauvegarde : vérifiez les données.')
    }
  }

  return (
    <div className="page inventory-page">
      <div className="page-header">
        <h2>Gestion des entrées / sorties</h2>
      </div>
      <div className="panel form-panel">
        <label>
          Type d'équipement
          <select value={item.type} onChange={e => setItem({ ...item, type: e.target.value })}>
            <option>Desktop</option>
            <option>Laptop</option>
            <option>Ecran</option>
            <option>Other</option>
          </select>
        </label>
        <label>
          Quantité
          <input type="number" min="1" value={item.quantity} onChange={e => setItem({ ...item, quantity: e.target.value })} />
        </label>
        <label>
          Numéro de série
          <input value={item.serial_number} onChange={e => setItem({ ...item, serial_number: e.target.value })} />
        </label>
        <label>
          Modèle
          <input value={item.model} onChange={e => setItem({ ...item, model: e.target.value })} />
        </label>
        <label>
          Destination
          <input value={item.destination} onChange={e => setItem({ ...item, destination: e.target.value })} placeholder="Salle, agence, service..." />
        </label>
        <label>
          Notes
          <textarea value={item.notes} onChange={e => setItem({ ...item, notes: e.target.value })} />
        </label>
        {message && <div className="info-message">{message}</div>}
        <div className="button-row">
          <button type="button" onClick={() => handleSubmit(submitEntry, 'Entrée')}>Ajouter entrée</button>
          <button type="button" onClick={() => handleSubmit(submitExit, 'Sortie')}>Ajouter sortie</button>
        </div>
      </div>
    </div>
  )
}
