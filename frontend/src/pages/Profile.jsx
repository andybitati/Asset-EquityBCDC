import { useEffect, useState } from 'react'
import { createUser, deleteUser, fetchUsers, updateCurrentUser, updateUser, uploadUserPhoto } from '../services/api'
import { resolvePhotoUrl } from '../utils/photo'

const avatarOptions = [
  '/avatar-admin.svg',
  '/avatar-manager.svg',
  '/avatar-user-red.svg',
  '/avatar-user-gold.svg',
  '/avatar-user-gray.svg',
  '/avatar-auditor.svg',
]

const roleOptions = [
  { value: 'user', label: 'Utilisateur' },
  { value: 'manager', label: 'Responsable' },
  { value: 'auditor', label: 'Auditeur' },
  { value: 'admin', label: 'Administrateur' },
]

const MAX_PROFILE_PHOTO_BYTES = 2 * 1024 * 1024
const PROFILE_PHOTO_MAX_SIDE = 768

function defaultForm(user) {
  return {
    username: user?.username || '',
    display_name: user?.display_name || '',
    photo_url: user?.photo_url || '',
    current_password: '',
    new_password: '',
  }
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(new Error('Lecture de la photo impossible.'))
    reader.readAsDataURL(file)
  })
}

function loadImage(dataUrl) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('Photo illisible.'))
    image.src = dataUrl
  })
}

function dataUrlSize(dataUrl) {
  const base64 = dataUrl.split(',')[1] || ''
  return Math.ceil((base64.length * 3) / 4)
}

async function compressProfilePhoto(file) {
  const originalDataUrl = await readFileAsDataUrl(file)
  if (file.size <= MAX_PROFILE_PHOTO_BYTES && dataUrlSize(originalDataUrl) <= MAX_PROFILE_PHOTO_BYTES) {
    return { filename: file.name, dataUrl: originalDataUrl, compressed: false }
  }

  const image = await loadImage(originalDataUrl)
  const scale = Math.min(1, PROFILE_PHOTO_MAX_SIDE / Math.max(image.width, image.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(image.width * scale))
  canvas.height = Math.max(1, Math.round(image.height * scale))

  const context = canvas.getContext('2d')
  context.fillStyle = '#ffffff'
  context.fillRect(0, 0, canvas.width, canvas.height)
  context.drawImage(image, 0, 0, canvas.width, canvas.height)

  for (const quality of [0.86, 0.78, 0.7, 0.62, 0.54, 0.46]) {
    const dataUrl = canvas.toDataURL('image/jpeg', quality)
    if (dataUrlSize(dataUrl) <= MAX_PROFILE_PHOTO_BYTES) {
      return {
        filename: file.name.replace(/\.[^.]+$/, '') + '.jpg',
        dataUrl,
        compressed: true,
      }
    }
  }

  throw new Error('La photo reste trop lourde après compression. Choisissez une image plus petite.')
}

export default function ProfilePage({ token, user, refresh }) {
  const [form, setForm] = useState(defaultForm(user))
  const [newUser, setNewUser] = useState({ username: '', display_name: '', password: '', role: 'user', photo_url: '' })
  const [users, setUsers] = useState([])
  const [message, setMessage] = useState(null)
  const canEditOwnProfile = user?.role !== 'auditor'

  const uploadPhoto = async (file, applyPhotoUrl, options = {}) => {
    if (!file) return
    setMessage(null)
    try {
      const photo = await compressProfilePhoto(file)
      const response = await uploadUserPhoto(token, {
        filename: photo.filename,
        data_url: photo.dataUrl,
        target_username: options.targetUsername || null,
        persist: options.persist !== false,
      })
      applyPhotoUrl(response.photo_url)
      if (options.persist !== false) {
        refresh()
      }
      const savedText = options.persist === false ? 'chargée' : 'enregistrée'
      setMessage(photo.compressed ? `Photo compressée et ${savedText}.` : `Photo ${savedText}.`)
    } catch (err) {
      setMessage(err.message || 'Upload de la photo impossible.')
    }
  }

  useEffect(() => {
    setForm(defaultForm(user))
  }, [user])

  useEffect(() => {
    if (user?.role === 'admin') {
      fetchUsers(token).then(data => setUsers(data.users || [])).catch(() => setUsers([]))
    }
  }, [token, user])

  const saveProfile = async () => {
    setMessage(null)
    try {
      const payload = {
        username: form.username,
        display_name: form.display_name,
        photo_url: form.photo_url,
        current_password: form.current_password || null,
        new_password: form.new_password || null,
      }
      await updateCurrentUser(token, payload)
      setMessage('Profil mis à jour.')
      setForm(prev => ({ ...prev, current_password: '', new_password: '' }))
      refresh()
    } catch (err) {
      setMessage("Modification refusée : vérifiez la règle des 3 mois ou les informations saisies.")
    }
  }

  const saveUser = async target => {
    setMessage(null)
    try {
      await updateUser(token, target.original_username || target.username, {
        username: target.username,
        display_name: target.display_name,
        role: target.role,
        photo_url: target.photo_url,
        is_active: target.is_active,
      })
      setMessage('Utilisateur mis à jour.')
      const data = await fetchUsers(token)
      setUsers(data.users || [])
      refresh()
    } catch (err) {
      setMessage("Impossible de modifier cet utilisateur.")
    }
  }

  const addUser = async () => {
    setMessage(null)
    try {
      await createUser(token, newUser)
      setMessage('Utilisateur créé.')
      setNewUser({ username: '', display_name: '', password: '', role: 'user', photo_url: '' })
      const data = await fetchUsers(token)
      setUsers(data.users || [])
    } catch (err) {
      setMessage("Création refusée : vérifiez les champs et la règle du mot de passe.")
    }
  }

  const removeUser = async username => {
    setMessage(null)
    try {
      await deleteUser(token, username)
      setMessage('Utilisateur supprimé.')
      setUsers(users.filter(item => item.username !== username))
    } catch (err) {
      setMessage("Suppression impossible.")
    }
  }

  return (
    <div className="page profile-page">
      <div className="page-header">
        <h2>Profil et utilisateurs</h2>
      </div>

      <div className="panel profile-panel">
        <div className="profile-preview">
          <img src={resolvePhotoUrl(form.photo_url)} alt={form.display_name || form.username} />
          <div>
            <h3>{form.display_name || form.username}</h3>
            <span>{user?.role || 'user'}</span>
          </div>
        </div>
        <div className="form-panel compact-form">
          <label>
            Identifiant
            <input value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} disabled={!canEditOwnProfile} />
          </label>
          <label>
            Nom affiché
            <input value={form.display_name} onChange={e => setForm({ ...form, display_name: e.target.value })} disabled={!canEditOwnProfile} />
          </label>
          <label>
            Photo utilisateur
            <input value={form.photo_url} onChange={e => setForm({ ...form, photo_url: e.target.value })} placeholder="URL ou chemin de la photo" disabled={!canEditOwnProfile} />
          </label>
          {canEditOwnProfile && (
            <div className="photo-tools">
              <span>Choisir un avatar</span>
              <div className="avatar-picker">
                {avatarOptions.map(avatar => (
                  <button
                    type="button"
                    key={avatar}
                    className={form.photo_url === avatar ? 'selected' : ''}
                    onClick={() => setForm({ ...form, photo_url: avatar })}
                    aria-label="Choisir cet avatar"
                  >
                    <img src={avatar} alt="" />
                  </button>
                ))}
              </div>
              <label className="file-upload">
                Charger une photo locale
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  onChange={e => uploadPhoto(e.target.files?.[0], photo_url => setForm(prev => ({ ...prev, photo_url })))}
                />
              </label>
            </div>
          )}
          <label>
            Mot de passe actuel
            <input type="password" value={form.current_password} onChange={e => setForm({ ...form, current_password: e.target.value })} disabled={!canEditOwnProfile} />
          </label>
          <label>
            Nouveau mot de passe
            <input type="password" value={form.new_password} onChange={e => setForm({ ...form, new_password: e.target.value })} disabled={!canEditOwnProfile} />
          </label>
          <p className="form-hint">{canEditOwnProfile ? 'Hors admin, les identifiants ne peuvent être modifiés qu’une fois tous les 3 mois. Le mot de passe doit contenir 8 caractères, une majuscule, un chiffre et un caractère spécial.' : 'Le rôle auditeur est en lecture seule.'}</p>
          {canEditOwnProfile && <button type="button" onClick={saveProfile}>Enregistrer mon profil</button>}
        </div>
      </div>

      {user?.role === 'admin' && (
        <div className="panel table-panel">
          <div className="panel-heading">
            <h3>Gestion des utilisateurs</h3>
            <span>L’admin ne peut pas changer le mot de passe d’un autre utilisateur.</span>
          </div>
          <div className="user-create-grid">
            <input value={newUser.username} onChange={e => setNewUser({ ...newUser, username: e.target.value })} placeholder="Identifiant" />
            <input value={newUser.display_name} onChange={e => setNewUser({ ...newUser, display_name: e.target.value })} placeholder="Nom affiché" />
            <input type="password" value={newUser.password} onChange={e => setNewUser({ ...newUser, password: e.target.value })} placeholder="Mot de passe initial" />
            <select value={newUser.role} onChange={e => setNewUser({ ...newUser, role: e.target.value })} aria-label="Rôle du nouvel utilisateur">
              {roleOptions.map(role => (
                <option key={role.value} value={role.value}>{role.label}</option>
              ))}
            </select>
            <input value={newUser.photo_url} onChange={e => setNewUser({ ...newUser, photo_url: e.target.value })} placeholder="Photo URL" />
            <button type="button" onClick={addUser}>Créer utilisateur</button>
          </div>
          <div className="admin-photo-tools">
            <span>Photo du nouvel utilisateur</span>
            <div className="avatar-picker">
              {avatarOptions.map(avatar => (
                <button
                  type="button"
                  key={avatar}
                  className={newUser.photo_url === avatar ? 'selected' : ''}
                  onClick={() => setNewUser({ ...newUser, photo_url: avatar })}
                  aria-label="Choisir cet avatar"
                >
                  <img src={avatar} alt="" />
                </button>
              ))}
            </div>
            <label className="file-upload compact">
              Upload local
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                onChange={e => uploadPhoto(e.target.files?.[0], photo_url => setNewUser(prev => ({ ...prev, photo_url })), { persist: false })}
              />
            </label>
          </div>
          <table>
            <thead>
              <tr>
                <th>Photo</th>
                <th>Identifiant</th>
                <th>Nom</th>
                <th>Rôle</th>
                <th>Actif</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(item => (
                <tr key={item.username}>
                  <td>
                    <div className="table-photo-editor">
                      <img className="table-avatar" src={resolvePhotoUrl(item.photo_url)} alt={item.display_name} />
                      <select
                        value={item.photo_url || ''}
                        onChange={e => setUsers(users.map(row => row.username === item.username ? { ...row, photo_url: e.target.value } : row))}
                      >
                        <option value="">Avatar par défaut</option>
                        {avatarOptions.map(avatar => (
                          <option key={avatar} value={avatar}>{avatar.replace('/', '').replace('.svg', '')}</option>
                        ))}
                      </select>
                      <label className="file-upload compact">
                        Upload
                        <input
                          type="file"
                          accept="image/png,image/jpeg,image/webp,image/gif"
                          onChange={e => uploadPhoto(
                            e.target.files?.[0],
                            photo_url => setUsers(users.map(row => row.username === item.username ? { ...row, photo_url } : row)),
                            { targetUsername: item.original_username || item.username },
                          )}
                        />
                      </label>
                    </div>
                  </td>
                  <td><input value={item.username} onChange={e => setUsers(users.map(row => row.username === item.username ? { ...row, original_username: row.original_username || row.username, username: e.target.value } : row))} /></td>
                  <td><input value={item.display_name} onChange={e => setUsers(users.map(row => row.username === item.username ? { ...row, display_name: e.target.value } : row))} /></td>
                  <td>
                    <select value={item.role} onChange={e => setUsers(users.map(row => row.username === item.username ? { ...row, role: e.target.value } : row))}>
                      {roleOptions.map(role => (
                        <option key={role.value} value={role.value}>{role.label}</option>
                      ))}
                    </select>
                  </td>
                  <td><input type="checkbox" checked={item.is_active} onChange={e => setUsers(users.map(row => row.username === item.username ? { ...row, is_active: e.target.checked } : row))} /></td>
                  <td className="action-cell">
                    <button type="button" onClick={() => saveUser(item)}>Sauver</button>
                    <button type="button" className="danger-button" onClick={() => removeUser(item.username)}>Supprimer</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {message && <div className="info-message">{message}</div>}
    </div>
  )
}
