import { useEffect, useMemo, useState } from 'react'
import { importEntrySerialNumbers, submitEntry, submitExit } from '../services/api'
import { normalizeBusinessText } from '../utils/text'

const defaultItem = {
  type: '',
  quantity: '',
  serial_numbers: '',
  import_file: null,
  notes: '',
}

const equipmentTypes = [
  'Adaptateur',
  "Cable d'alimentation",
  'Cable HDMI (15m)',
  'Cable HDMI (30m)',
  'Cable HDMI (3m)',
  'Cable HDMI (5m)',
  'Cable locker',
  'Cable locker (noir)',
  'Casque',
  'Chargeur Laptop Tige',
  'Chargeur Laptop Type C',
  'Desktop',
  'Desktop complet (Region Ouest)',
  'Desktop complet EDRMS',
  'DVD/CD-R',
  'Extratime',
  'Finger',
  'Flash Disk 16GB',
  'Imprimante Bixolon',
  'Imprimante Evolis',
  'Imprimante Evolis (Libanga)',
  'Kit Starlink',
  'Laptop OmniBook',
  'Laptop OmniBook (Region Ouest)',
  'Laptop Pavillon',
  'Laptop ProBook',
  'Laptop ProBook (Libanga)',
  'Laptop ProBook (EDRMS)',
  'Laptop ProBook (Region Ouest)',
  'Lecteur DVD/CD externe Tecsa',
  'Moniteur',
  'Moniteur Diagonal 24 pouces',
  'Pen BK',
  'Rouleau Extratime',
  'Routeur',
  'Ruban Bixolon',
  'Ruban monochrome (black 1)',
  'Ruban monochrome (black 2)',
  'Ruban monochrome (couleur)',
  'Ruban monochrome (white)',
  'Sac Laptop',
  'Scanner biometrique (Kojak)',
  'Scanner Ricoh',
  'Souris avec fil',
  'Souris sans fil (avec pile)',
  'Souris sans fil (sans pile)',
  'Support Laptop',
  'Switch 24 ports',
  'Switch 48 ports',
  'Unité Centrale',
  'Webcam',
]

const serializedTypes = new Set([
  'Desktop',
  'Desktop complet (Region Ouest)',
  'Desktop complet EDRMS',
  'Finger',
  'Imprimante Bixolon',
  'Imprimante Evolis',
  'Imprimante Evolis (Libanga)',
  'Laptop OmniBook',
  'Laptop OmniBook (Region Ouest)',
  'Laptop Pavillon',
  'Laptop ProBook',
  'Laptop ProBook (Libanga)',
  'Laptop ProBook (EDRMS)',
  'Laptop ProBook (Region Ouest)',
  'Moniteur',
  'Moniteur Diagonal 24 pouces',
  'Routeur',
  'Scanner biometrique (Kojak)',
  'Scanner Ricoh',
  'Switch 24 ports',
  'Switch 48 ports',
  'Unité Centrale',
  'Webcam',
])

const defaultExit = {
  stockKey: '',
  serialRegistryId: '',
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

function parseSerialText(value) {
  return value
    .split(/[\n,;]+/)
    .map(item => item.trim())
    .filter(Boolean)
}

export default function InventoryPage({ token, stockItems = [], serialRegistry = { items: [] }, user, refresh }) {
  const [entry, setEntry] = useState(defaultItem)
  const [exitItem, setExitItem] = useState(defaultExit)
  const [message, setMessage] = useState(null)
  const [importReport, setImportReport] = useState(null)
  const [exitNotification, setExitNotification] = useState(null)

  const availableItems = useMemo(() => stockItems.filter(item => item.quantity > 0), [stockItems])
  const availableSerials = useMemo(() => (serialRegistry.items || [])
    .filter(item => item.status === 'in_stock')
    .sort((a, b) => a.equipment_type.localeCompare(b.equipment_type) || a.serial_number.localeCompare(b.serial_number)), [serialRegistry])
  const selectedStockItem = availableItems.find(item => makeStockKey(item) === exitItem.stockKey)
  const selectedSerial = availableSerials.find(item => String(item.id) === exitItem.serialRegistryId)
  const entrySerialNumbers = useMemo(() => parseSerialText(entry.serial_numbers), [entry.serial_numbers])
  const entryRequiresSerials = serializedTypes.has(entry.type)
  const selectedRequiresSerials = Boolean(selectedStockItem && serializedTypes.has(selectedStockItem.equipment_type))
  const canImportSerials = entryRequiresSerials && (user?.role === 'admin' || user?.role === 'manager')
  const serialCounts = serialRegistry.counts || {}

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
    setImportReport(null)
    setExitNotification(null)
    if (!entry.type) {
      setMessage("Veuillez choisir le type d'équipement à ajouter.")
      return
    }
    if (!entry.quantity || Number(entry.quantity) < 1) {
      setMessage("Veuillez renseigner une quantité d'entrée valide.")
      return
    }
    const serialNumbers = entrySerialNumbers
    if (entryRequiresSerials && serialNumbers.length !== Number(entry.quantity)) {
      setMessage(`Ce matériel exige un numéro de série par unité. Quantité: ${entry.quantity}, séries: ${serialNumbers.length}.`)
      return
    }
    if (!entryRequiresSerials && serialNumbers.length) {
      setMessage('Les numéros de série ne sont acceptés que pour les matériels traçables individuellement.')
      return
    }
    if (serialNumbers.length > Number(entry.quantity)) {
      setMessage("Le nombre de numéros de série ne peut pas dépasser la quantité entrée.")
      return
    }
    try {
      const payload = {
        type: entry.type,
        quantity: Number(entry.quantity),
        serial_numbers: serialNumbers,
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

  const handleSerialImport = async () => {
    setMessage(null)
    setImportReport(null)
    setExitNotification(null)
    if (!entry.type) {
      setMessage("Veuillez choisir le type d'équipement avant d'importer.")
      return
    }
    if (!entry.import_file) {
      setMessage('Veuillez choisir un fichier CSV ou XLS à importer.')
      return
    }
    try {
      const result = await importEntrySerialNumbers(token, {
        type: entry.type,
        file: entry.import_file,
        notes: entry.notes,
      })
      setExitNotification({
        status: 'approved',
        title: 'Import réussi',
        text: `${result.imported} numéro${result.imported > 1 ? 's' : ''} importé${result.imported > 1 ? 's' : ''}.`,
        icon: '/approuvee.jpg',
      })
      setImportReport(result)
      window.setTimeout(() => setEntry(defaultItem), 900)
      refresh()
    } catch (err) {
      setMessage(err?.message || "Erreur d'import : vérifiez le fichier.")
    }
  }

  const handleExitSubmit = async () => {
    setMessage(null)
    setExitNotification(null)
    if (!selectedStockItem) {
      setExitNotification(buildRefusal('aucun matériel disponible à sortir.'))
      return
    }
    if (selectedRequiresSerials && !exitItem.serial_number.trim()) {
      setExitNotification(buildRefusal('le numéro de série est obligatoire pour identifier ce matériel traçable.'))
      return
    }
    if (selectedRequiresSerials && !exitItem.model.trim()) {
      setExitNotification(buildRefusal('le modèle est obligatoire pour identifier ce matériel traçable.'))
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
    if (selectedRequiresSerials && Number(exitItem.quantity) !== 1) {
      setExitNotification(buildRefusal('une sortie avec numéro de série doit concerner une seule unité.'))
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
        serial_number: selectedRequiresSerials ? (exitItem.serial_number || selectedStockItem.serial_number || '') : '',
        model: selectedRequiresSerials ? (exitItem.model || selectedStockItem.model || '') : exitItem.model,
        destination: exitItem.destination,
        taken_by: exitItem.taken_by,
        notes: exitItem.notes,
      }
      const result = await submitExit(token, payload)
      const reviewRequired = result.manager_review?.manager_review_required
      setExitNotification({
        status: reviewRequired ? 'review' : 'approved',
        title: reviewRequired ? 'Sortie enregistrée - avis responsable requis' : 'Sortie approuvée',
        text: reviewRequired
          ? `Stock restant ${result.manager_review.remaining_stock}, réserve ${result.manager_review.emergency_reserve_threshold}.`
          : 'La sortie du matériel a été enregistrée avec succès.',
        icon: reviewRequired ? '/refusee.jpg' : '/approuvee.jpg',
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
      <div className="operation-strip">
        <div>
          <span>Séries disponibles</span>
          <strong>{serialCounts.in_stock || availableSerials.length}</strong>
        </div>
        <div>
          <span>Séries sorties</span>
          <strong>{serialCounts.exited || 0}</strong>
        </div>
        <div>
          <span>Matériels en stock</span>
          <strong>{availableItems.length}</strong>
        </div>
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
              value={entry.quantity || (entrySerialNumbers.length ? String(entrySerialNumbers.length) : '')}
              onChange={e => setEntry({ ...entry, quantity: e.target.value })}
              placeholder="Exemple : 5"
            />
          </label>
          {entryRequiresSerials ? (
            <>
              <div className="form-hint strong-hint">Numéro de série obligatoire pour chaque unité de ce matériel.</div>
              <label>
                Numéros de série reçus
                <textarea
                  value={entry.serial_numbers}
                  onChange={e => {
                    const serials = parseSerialText(e.target.value)
                    setEntry({ ...entry, serial_numbers: e.target.value, quantity: serials.length ? String(serials.length) : entry.quantity })
                  }}
                  placeholder="Un numéro par ligne, ou séparés par virgules"
                />
              </label>
            </>
          ) : (
            <div className="form-hint">Ce type est géré en quantité globale, sans registre de numéro de série.</div>
          )}
          {canImportSerials && (
            <>
              <label>
                Import CSV / XLS
                <input
                  type="file"
                  accept=".csv,.xls,text/csv,application/vnd.ms-excel"
                  onChange={e => setEntry({ ...entry, import_file: e.target.files?.[0] || null })}
                />
              </label>
              <button type="button" onClick={handleSerialImport}>Importer numéros de série</button>
              {importReport && (
                <div className="import-report">
                  <span>{importReport.imported || 0} importé(s)</span>
                  <span>{(importReport.duplicates || []).length} doublon(s)</span>
                  <span>{(importReport.already_exited || []).length} déjà sorti(s)</span>
                </div>
              )}
            </>
          )}
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
            Numéro de série disponible
            <select
              value={exitItem.serialRegistryId}
              onChange={e => {
                const serial = availableSerials.find(item => String(item.id) === e.target.value)
                const stockItem = availableItems.find(item => (
                  item.equipment_type === serial?.equipment_type
                  && item.serial_number === serial?.serial_number
                )) || availableItems.find(item => item.equipment_type === serial?.equipment_type)
                setExitItem({
                  ...exitItem,
                  serialRegistryId: e.target.value,
                  stockKey: stockItem ? makeStockKey(stockItem) : '',
                  quantity: serial ? '1' : '',
                  serial_number: serial?.serial_number || '',
                  model: '',
                })
              }}
              disabled={!availableSerials.length}
            >
              <option value="">{availableSerials.length ? 'Choisir une série en stock' : 'Aucune série disponible'}</option>
              {availableSerials.map(item => (
                <option key={item.id} value={item.id}>
                  {item.equipment_type} - {normalizeBusinessText(item.serial_number)} (ID {item.id})
                </option>
              ))}
            </select>
          </label>
          <label>
            Matériel en stock
            <select
              value={exitItem.stockKey}
              onChange={e => {
                const stockItem = availableItems.find(item => makeStockKey(item) === e.target.value)
                setExitItem({
                  ...exitItem,
                  stockKey: e.target.value,
                  serialRegistryId: '',
                  quantity: stockItem ? '1' : '',
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
              {selectedSerial && <span>ID série entrée: {selectedSerial.id}</span>}
              <span>Série: {normalizeBusinessText(selectedStockItem.serial_number) || '-'}</span>
              {selectedSerial && <span>Série registre: {normalizeBusinessText(selectedSerial.serial_number)}</span>}
              <span>Modèle: {normalizeBusinessText(selectedStockItem.model) || '-'}</span>
              <span>Quantité disponible: {selectedStockItem.quantity}</span>
            </div>
          )}
          {selectedRequiresSerials && (
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
          )}
          <label>
            {selectedRequiresSerials ? 'Modèle à la sortie' : 'Modèle / référence'}
            <input
              value={exitItem.model}
              onChange={e => setExitItem({ ...exitItem, model: e.target.value })}
              placeholder={selectedRequiresSerials ? 'Obligatoire pour valider la sortie' : 'Facultatif'}
              disabled={!selectedStockItem}
              required={selectedRequiresSerials}
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
