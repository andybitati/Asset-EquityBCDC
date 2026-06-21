# Procédure de connexion MySQL en production

Cette procédure décrit comment préparer une machine cible pour exécuter Assets Equity BCDC avec une base MySQL de production.

## 1. Préparer MySQL

Sur la machine qui héberge la base :

1. Ouvrir MySQL Workbench ou le client MySQL autorisé.
2. Se connecter avec un compte administrateur MySQL.
3. Exécuter le script :

```text
backend/mysql-init.sql
```

Ce script crée :

- la base `asset_equity` ;
- l’utilisateur applicatif `asset_equity_user` ;
- les tables applicatives ;
- les types de matériels ;
- les comptes initiaux.

## 2. Vérifier la base

Dans MySQL Workbench :

```sql
SHOW DATABASES;
USE asset_equity;
SHOW TABLES;
```

Les tables minimales attendues sont :

```text
audit_logs
equipment_types
materials
movements
sessions
users
```

## 3. Configurer le fichier `.env`

Sur la machine applicative, créer ou modifier :

```text
backend/.env
```

Exemple local :

```env
DATABASE_URL=mysql+pymysql://asset_equity_user:ChangeMe123!@127.0.0.1:3306/asset_equity
CORS_ORIGINS=http://localhost:48621,http://127.0.0.1:48621
SESSION_TTL_MINUTES=60
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCK_MINUTES=15
LOG_LEVEL=INFO
```

Exemple réseau :

```env
DATABASE_URL=mysql+pymysql://asset_equity_user:MotDePasseFort@IP_DU_SERVEUR_MYSQL:3306/asset_equity
CORS_ORIGINS=http://IP_DU_POSTE:48621
```

## 4. Vérifier la connexion depuis l’application

Depuis la racine du projet :

```powershell
.\venv\Scripts\python.exe -c "from backend.app.main import app; print(app.title)"
```

Si la connexion est correcte, le backend démarre sans erreur.

## 5. Lancer l’application

```powershell
.\start-all.bat
```

Backend :

```text
http://localhost:48620
```

Frontend :

```text
http://localhost:48621
```

## 6. Points obligatoires en production bancaire

- Ne jamais utiliser le compte MySQL `root` dans `DATABASE_URL`.
- Remplacer `ChangeMe123!` par un mot de passe fort.
- Limiter l’accès MySQL au réseau interne autorisé.
- Sauvegarder la base avant migration.
- Activer HTTPS via reverse proxy ou serveur frontal.
- Stocker `.env` hors Git et avec permissions restreintes.
- Planifier `scripts/BackupMySql.ps1`.
