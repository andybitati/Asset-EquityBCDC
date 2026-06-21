import { useEffect, useMemo, useState } from 'react'
import { submitEntry, submitExit } from '../services/api'

const defaultItem = {
  type: 'Desktop',
  quantity: 1,
  serial_number: '',
  model: '',
  destination: '',
  taken_by: '',
  notes: '',
}

const equipmentTypes = ['Desktop', 'Laptop', 'Ecran', 'Souris', 'Switch', 'Routeur', 'Clavier', 'Other']

const defaultExit = {
  stockKey: '',
  quantity: 1,
  destination: '',
  taken_by: '',
  notes: '',
}

function makeStockKey(item) {
  return String(item.material_id)
}

function stockLabel(item) {
  const details = [item.serial_number, item.model].filter(Boolean).join(' / ')
  return details
    ? `${item.equipment_type} - ${details} (${item.quantity} disponible${item.quantity > 1 ? 's' : ''})`
    : `${item.equipment_type} (${item.quantity} disponible${item.quantity > 1 ? 's' : ''})`
}

export default function InventoryPage({ token, stockItems = [], refresh }) {
  const [entry, setEntry] = useState(defaultItem)
  const [exitItem, setExitItem] = useState(defaultExit)
  const [message, setMessage] = useState(null)

  const availableItems = useMemo(() => stockItems.filter(item => item.quantity > 0), [stockItems])
  const selectedStockItem = availableItems.find(item => makeStockKey(item) === exitItem.stockKey)

  useEffect(() => {
    if (!availableItems.length) {
      setExitItem(prev => ({ ...prev, stockKey: '' }))
      return
    }
    if (!availableItems.some(item => makeStockKey(item) === exitItem.stockKey)) {
      setExitItem(prev => ({ ...prev, stockKey: makeStockKey(availableItems[0]), quantity: 1 }))
    }
  }, [availableItems, exitItem.stockKey])

  const handleEntrySubmit = async () => {
    setMessage(null)
    try {
      const payload = {
        type: entry.type,
        quantity: Number(entry.quantity),
        serial_number: entry.serial_number,
        model: entry.model,
        destination: entry.destination,
        taken_by: entry.taken_by,
        notes: entry.notes,
      }
      await submitEntry(token, payload)
      setMessage('Entrée enregistrée avec succès')
      setEntry(defaultItem)
      refresh()
    } catch (err) {
      setMessage("Erreur de sauvegarde de l'entrée : vérifiez les données.")
    }
  }

  const handleExitSubmit = async () => {
    setMessage(null)
    if (!selectedStockItem) {
      setMessage('Aucun matériel disponible à sortir.')
      return
    }
    try {
      const payload = {
        material_id: selectedStockItem.material_id,
        type: selectedStockItem.equipment_type,
        quantity: Number(exitItem.quantity),
        serial_number: selectedStockItem.serial_number || '',
        model: selectedStockItem.model || '',
        destination: exitItem.destination,
        taken_by: exitItem.taken_by,
        notes: exitItem.notes,
      }
      await submitExit(token, payload)
      setMessage('Sortie enregistrée avec succès')
      setExitItem(defaultExit)
      refresh()
    } catch (err) {
      setMessage('Sortie refusée : ce matériel ou cette quantité ne se trouve pas dans le stock.')
    }
  }

  return (
    <div className="page inventory-page">
      <div className="page-header">
        <h2>Gestion des entrées / sorties</h2>
      </div>
      <div className="inventory-grid">
        <div className="panel form-panel">
          <h3 className="section-title">Nouvelle entrée</h3>
          <label>
            Type d'équipement
            <select value={entry.type} onChange={e => setEntry({ ...entry, type: e.target.value })}>
              {equipmentTypes.map(type => <option key={type}>{type}</option>)}
            </select>
          </label>
          <label>
            Quantité
            <input type="number" min="1" value={entry.quantity} onChange={e => setEntry({ ...entry, quantity: e.target.value })} />
          </label>
          <label>
            Numéro de série
            <input value={entry.serial_number} onChange={e => setEntry({ ...entry, serial_number: e.target.value })} />
          </label>
          <label>
            Modèle
            <input value={entry.model} onChange={e => setEntry({ ...entry, model: e.target.value })} />
          </label>
          <label>
            Destination
            <input value={entry.destination} onChange={e => setEntry({ ...entry, destination: e.target.value })} placeholder="Stock, salle, agence, service..." />
          </label>
          <label>
            Description / Notes
            <textarea value={entry.notes} onChange={e => setEntry({ ...entry, notes: e.target.value })} />
          </label>
          <button type="button" onClick={handleEntrySubmit}>Ajouter entrée</button>
        </div>

        <div className="panel form-panel">
          <h3 className="section-title">Nouvelle sortie</h3>
          <label>
            Matériel en stock
            <select
              value={exitItem.stockKey}
              onChange={e => setExitItem({ ...exitItem, stockKey: e.target.value, quantity: 1 })}
              disabled={!availableItems.length}
            >
              {!availableItems.length && <option>Aucun matériel disponible</option>}
              {availableItems.map(item => (
                <option key={makeStockKey(item)} value={makeStockKey(item)}>
                  {stockLabel(item)}
                </option>
              ))}
            </select>
          </label>
          {selectedStockItem && (
            <div className="stock-option">
              <strong>{selectedStockItem.equipment_type}</strong>
              <span>Série: {selectedStockItem.serial_number || '-'}</span>
              <span>Modèle: {selectedStockItem.model || '-'}</span>
              <span>Quantité disponible: {selectedStockItem.quantity}</span>
            </div>
          )}
          <label>
            Quantité à sortir
            <input
              type="number"
              min="1"
              max={selectedStockItem?.quantity || 1}
              value={exitItem.quantity}
              onChange={e => setExitItem({ ...exitItem, quantity: e.target.value })}
              disabled={!selectedStockItem}
            />
          </label>
          <label>
            Destination du matériel
            <input
              value={exitItem.destination}
              onChange={e => setExitItem({ ...exitItem, destination: e.target.value })}
              placeholder="Service, agence, bureau, dépôt..."
              disabled={!selectedStockItem}
            />
          </label>
          <label>
            Pris par
            <input
              value={exitItem.taken_by}
              onChange={e => setExitItem({ ...exitItem, taken_by: e.target.value })}
              placeholder="Nom de la personne responsable"
              disabled={!selectedStockItem}
            />
          </label>
          <label>
            Description de la sortie
            <textarea
              value={exitItem.notes}
              onChange={e => setExitItem({ ...exitItem, notes: e.target.value })}
              placeholder="Motif, ticket, commentaire, détails de remise..."
              disabled={!selectedStockItem}
            />
          </label>
          <button type="button" onClick={handleExitSubmit} disabled={!selectedStockItem}>Ajouter sortie</button>
        </div>
      </div>
      {message && <div className="info-message">{message}</div>}
    </div>
  )
}
