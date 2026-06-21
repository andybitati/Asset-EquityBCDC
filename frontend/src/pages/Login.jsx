import { useState } from 'react'
import { loginRequest } from '../services/api'

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
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
      setError(err?.message || 'Échec de l’authentification. Vérifiez vos identifiants.')
    }
  }

  const handleKeyDown = event => {
    if (event.key === 'Enter') {
      event.preventDefault()
      event.currentTarget.requestSubmit()
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <img className="auth-logo" src="/assets-equity-logo.png" alt="Assets Equity BCDC" />
        <h1>Assets EquityBCDC</h1>
        <p>Connexion requise pour accéder à la gestion du stock.</p>
        <form onSubmit={handleSubmit} onKeyDown={handleKeyDown}>
          <label>
            Identifiant
            <input
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Entrez votre identifiant"
              required
            />
          </label>
          <label className="password-label">
            Mot de passe
            <div className="password-field">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Entrez votre mot de passe"
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(prev => !prev)}
                aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                title={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
              >
                <img src="/oeil.jpg" alt="" />
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
