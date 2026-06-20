import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'

export default function DashboardPage({ inventory, forecast, refresh }) {
  const chartData = Object.entries(inventory).map(([name, value]) => ({ name, value }))
  const stockHistory = chartData.map((entry, index) => ({ day: `J-${index}`, stock: entry.value }))

  return (
    <div className="page dashboard-page">
      <div className="page-header">
        <h2>Tableau de bord</h2>
        <button onClick={refresh}>Actualiser</button>
      </div>
      <div className="grid two-up">
        <div className="panel">
          <h3>Stock actuel</h3>
          <div className="stock-list">
            {chartData.map(item => (
              <div key={item.name} className="stock-item">
                <span>{item.name}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </div>
        <div className="panel">
          <h3>Prévision</h3>
          {forecast ? (
            <div className="forecast-box">
              <div>Stock total: {forecast.current_stock}</div>
              <div>Sorties moyennes/jour: {forecast.average_daily_exit}</div>
              <div>Seuil de commande: {forecast.reorder_threshold}</div>
              <div>Jours estimés avant rupture: {forecast.estimated_days_to_empty || 'N/A'}</div>
              <div>Recommandation: {forecast.recommendation}</div>
            </div>
          ) : (
            <p>Chargement des données...</p>
          )}
        </div>
      </div>
      <div className="panel full-width">
        <h3>Évolution du stock</h3>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={stockHistory} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="day" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="stock" stroke="#b60f1e" strokeWidth={3} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="panel full-width">
        <h3>Comparaison des types</h3>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chartData} margin={{ top: 20, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#b60f1e" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
