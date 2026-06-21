import { useEffect, useMemo, useState } from 'react'
import { submitEntry, submitExit } from '../services/api'
import { normalizeBusinessText } from '../utils/text'

const defaultItem = {
  type: '',
  quantity: '',
  notes: '',
}

const equipmentTypes = ['Desktop', 'Laptop', 'Ecran', 'Souris', 'Switch', 'Routeur', 'Clavier', 'Other']

const defaultExit = {
  stockKey: '',
  quantity: '',
  serial_number: '',
  model: '',
  destination: '',
  taken_by: '',
  notes: '',
}

function makeStockKey(item) {
  return String(item.material_id)
}

function stockLabel(item) {
  const details = [item.serial_number, item.model].filter(Boolean).map(normalizeBusinessText).join(' / ')
  return details
    ? `${item.equipment_type} - ${details} (${item.quantity} disponible${item.quantity > 1 ? 's' : ''})`
    : `${item.equipment_type} (${item.quantity} disponible${item.quantity > 1 ? 's' : ''})`
}

function buildRefusal(statusText) {
  return {
    status: 'refused',
    title: 'Sortie refusée',
    text: `Raison : ${statusText}`,
    icon: '/refusee.jpg',
  }
}

export default function InventoryPage({ token, stockItems = [], refresh }) {
  const [entry, setEntry] = useState(defaultItem)
  const [exitItem, setExitItem] = useState(defaultExit)
  const [message, setMessage] = useState(null)
  const [exitNotification, setExitNotification] = useState(null)

  const availableItems = useMemo(() => stockItems.filter(item => item.quantity > 0), [stockItems])
  const selectedStockItem = availableItems.find(item => makeStockKey(item) === exitItem.stockKey)

  useEffect(() => {
    if (!availableItems.length) {
      setExitItem(prev => ({ ...prev, stockKey: '' }))
      return
    }
    if (exitItem.stockKey && !availableItems.some(item => makeStockKey(item) === exitItem.stockKey)) {
      setExitItem(defaultExit)
    }
  }, [availableItems, exitItem.stockKey])

  useEffect(() => {
    if (!exitNotification) return undefined
    const timer = window.setTimeout(() => setExitNotification(null), 5000)
    return () => window.clearTimeout(timer)
  }, [exitNotification])

  const handleEntrySubmit = async () => {
    setMessage(null)
    setExitNotification(null)
    if (!entry.type) {
      setMessage("Veuillez choisir le type d'équipement à ajouter.")
      return
    }
    if (!entry.quantity || Number(entry.quantity) < 1) {
      setMessage("Veuillez renseigner une quantité d'entrée valide.")
      return
    }
    try {
      const payload = {
        type: entry.type,
        quantity: Number(entry.quantity),
        notes: entry.notes,
      }
      await submitEntry(token, payload)
      setExitNotification({
        status: 'approved',
        title: 'Entrée réussie',
        text: 'Le matériel a été ajouté au stock avec succès.',
        icon: '/approuvee.jpg',
      })
      window.setTimeout(() => setEntry(defaultItem), 900)
      refresh()
    } catch (err) {
      setMessage("Erreur de sauvegarde de l'entrée : vérifiez les données.")
    }
  }

  const handleExitSubmit = async () => {
    setMessage(null)
    setExitNotification(null)
    if (!selectedStockItem) {
      setExitNotification(buildRefusal('aucun matériel disponible à sortir.'))
      return
    }
    if (!exitItem.serial_number.trim()) {
      setExitNotification(buildRefusal('le numéro de série est obligatoire pour identifier le matériel sorti.'))
      return
    }
    if (!exitItem.model.trim()) {
      setExitNotification(buildRefusal('le modèle est obligatoire pour identifier le matériel sorti.'))
      return
    }
    if (!exitItem.destination.trim()) {
      setExitNotification(buildRefusal('la destination du matériel est obligatoire.'))
      return
    }
    if (!exitItem.taken_by.trim()) {
      setExitNotification(buildRefusal('la personne qui prend le matériel doit être renseignée.'))
      return
    }
    if (!exitItem.quantity || Number(exitItem.quantity) < 1) {
      setExitNotification(buildRefusal('la quantité à sortir doit être au moins égale à 1.'))
      return
    }
    if (Number(exitItem.quantity) > selectedStockItem.quantity) {
      setExitNotification(buildRefusal(`quantité insuffisante. Stock disponible : ${selectedStockItem.quantity}.`))
      return
    }
    try {
      const payload = {
        material_id: selectedStockItem.material_id,
        type: selectedStockItem.equipment_type,
        quantity: Number(exitItem.quantity),
        serial_number: exitItem.serial_number || selectedStockItem.serial_number || '',
        model: exitItem.model || selectedStockItem.model || '',
        destination: exitItem.destination,
        taken_by: exitItem.taken_by,
        notes: exitItem.notes,
      }
      await submitExit(token, payload)
      setExitNotification({
        status: 'approved',
        title: 'Sortie approuvée',
        text: 'La sortie du matériel a été enregistrée avec succès.',
        icon: '/approuvee.jpg',
      })
      setExitItem(defaultExit)
      refresh()
    } catch (err) {
      const detail = err?.message || 'Ce matériel ou cette quantité ne se trouve pas dans le stock.'
      setExitNotification(buildRefusal(detail))
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
              <option value="">Choisir un type d'équipement</option>
              {equipmentTypes.map(type => <option key={type}>{type}</option>)}
            </select>
          </label>
          <label>
            Quantité
            <input
              type="number"
              min="1"
              value={entry.quantity}
              onChange={e => setEntry({ ...entry, quantity: e.target.value })}
              placeholder="Exemple : 5"
            />
          </label>
          <label>
            Description / Notes
            <textarea
              value={entry.notes}
              onChange={e => setEntry({ ...entry, notes: e.target.value })}
              placeholder="Exemple : Lot reçu pour réapprovisionnement du dépôt"
            />
          </label>
          <button type="button" onClick={handleEntrySubmit}>Ajouter entrée</button>
        </div>

        <div className="panel form-panel">
          <h3 className="section-title">Nouvelle sortie</h3>
          <label>
            Matériel en stock
            <select
              value={exitItem.stockKey}
              onChange={e => {
                const stockItem = availableItems.find(item => makeStockKey(item) === e.target.value)
                setExitItem({
                  ...exitItem,
                  stockKey: e.target.value,
                  quantity: '',
                  serial_number: stockItem?.serial_number || '',
                  model: stockItem?.model || '',
                })
              }}
              disabled={!availableItems.length}
            >
              <option value="">{availableItems.length ? 'Choisir un matériel en stock' : 'Aucun matériel disponible'}</option>
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
              <span>Série: {normalizeBusinessText(selectedStockItem.serial_number) || '-'}</span>
              <span>Modèle: {normalizeBusinessText(selectedStockItem.model) || '-'}</span>
              <span>Quantité disponible: {selectedStockItem.quantity}</span>
            </div>
          )}
          <label>
            Numéro de série à la sortie
            <input
              value={exitItem.serial_number}
              onChange={e => setExitItem({ ...exitItem, serial_number: e.target.value })}
              placeholder="Obligatoire pour valider la sortie"
              disabled={!selectedStockItem}
              required
            />
          </label>
          <label>
            Modèle à la sortie
            <input
              value={exitItem.model}
              onChange={e => setExitItem({ ...exitItem, model: e.target.value })}
              placeholder="Obligatoire pour valider la sortie"
              disabled={!selectedStockItem}
              required
            />
          </label>
          <label>
            Quantité à sortir
            <input
              type="number"
              min="1"
              max={selectedStockItem?.quantity || 1}
              value={exitItem.quantity}
              onChange={e => setExitItem({ ...exitItem, quantity: e.target.value })}
              placeholder="Exemple : 1"
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
      {exitNotification && (
        <div className={`exit-notification ${exitNotification.status}`} role="status" aria-live="polite">
          <img src={exitNotification.icon} alt="" />
          <div>
            <strong>{exitNotification.title}</strong>
            <span>{exitNotification.text}</span>
          </div>
        </div>
      )}
    </div>
  )
}
