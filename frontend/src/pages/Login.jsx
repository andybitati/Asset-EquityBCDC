import { useState } from 'react'
import { loginRequest } from '../services/api'

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async event => {
    event.preventDefault()
    setError(null)
    try {
      const result = await loginRequest({ username, password })
      onLogin(result.access_token)
    } catch (err) {
      setError('Échec de l’authentification. Vérifiez vos identifiants.')
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Assets EquityBCDC</h1>
        <p>Connexion requise pour accéder à la gestion du stock.</p>
        <form onSubmit={handleSubmit}>
          <label>
            Identifiant
            <input value={username} onChange={e => setUsername(e.target.value)} required />
          </label>
          <label className="password-label">
            Mot de passe
            <div className="password-field">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(prev => !prev)}
              >
                {showPassword ? 'Masquer' : 'Voir'}
              </button>
            </div>
          </label>
          {error && <div className="error-message">{error}</div>}
          <button type="submit">Se connecter</button>
        </form>
      </div>
    </div>
  )
}
