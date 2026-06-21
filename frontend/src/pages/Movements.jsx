import { normalizeBusinessText } from '../utils/text'

export default function MovementsPage({ movements }) {
  return (
    <div className="page movements-page">
      <div className="page-header">
        <h2>Historique des mouvements</h2>
      </div>
      <div className="panel table-panel">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Type</th>
              <th>Équipement</th>
              <th>Quantité</th>
              <th>Série / Modèle</th>
              <th>Destination</th>
              <th>Pris par</th>
              <th>Initié par</th>
              <th>Description</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {movements.map(record => (
              <tr key={record.id}>
                <td>{record.id}</td>
                <td>{record.movement_type}</td>
                <td>{record.equipment_type}</td>
                <td>{record.quantity}</td>
                <td>{normalizeBusinessText(record.serial_number) || '-'} / {normalizeBusinessText(record.model) || '-'}</td>
                <td>{normalizeBusinessText(record.destination) || '-'}</td>
                <td>{normalizeBusinessText(record.taken_by) || '-'}</td>
                <td>{record.initiated_by || '-'}</td>
                <td>{normalizeBusinessText(record.notes) || '-'}</td>
                <td>{new Date(record.timestamp).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
