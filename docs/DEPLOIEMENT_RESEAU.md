# Deploiement reseau - Assets Equity BCDC

Cette procedure prepare une version parallele accessible depuis les postes du meme reseau interne.

## 1. Preparer la configuration reseau

Depuis la racine du projet, copier le modele :

```powershell
Copy-Item backend\network.env.example backend\network.env
```

Adapter `backend\network.env` si necessaire :

- garder `STORAGE_DIR=data\network` pour separer les donnees de la version locale ;
- definir `DATABASE_URL` si la version reseau doit utiliser MySQL ;
- definir `ASSET_EQUITY_PUBLIC_URL` si le serveur a un nom DNS interne ;
- definir les certificats `ASSET_EQUITY_SSL_CERTFILE` et `ASSET_EQUITY_SSL_KEYFILE` si HTTPS est active.

## 2. Lancer la version reseau

Double-cliquer sur :

```text
start-network.bat
```

Ou lancer :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\StartNetwork.ps1
```

Le script compile le frontend, demarre le backend en mode production et affiche deux liens :

```text
Lien local  : http://127.0.0.1:48620
Lien reseau : http://ADRESSE_IP_DU_SERVEUR:48620
```

Les utilisateurs du reseau doivent ouvrir le `Lien reseau`.

## 3. Autoriser le port dans le pare-feu Windows

Sur la machine serveur, autoriser le port `48620` en entree pour le reseau prive/interne.

Exemple PowerShell en administrateur :

```powershell
New-NetFirewallRule -DisplayName "Assets Equity BCDC" -Direction Inbound -Protocol TCP -LocalPort 48620 -Action Allow
```

## 4. Utiliser MySQL en production

Pour une vraie utilisation multi-postes, MySQL est recommande.

1. Executer `backend\mysql-init.sql` dans MySQL.
2. Renseigner `DATABASE_URL` dans `backend\network.env`.
3. Relancer `start-network.bat`.

Voir aussi [PRODUCTION_DB_SETUP.md](PRODUCTION_DB_SETUP.md).

## 5. Points importants

- Laisser la fenetre du serveur ouverte pendant l'utilisation.
- Ne pas exposer ce port directement sur Internet.
- Remplacer les mots de passe initiaux avant une utilisation reelle.
- Sauvegarder regulierement la base MySQL ou le dossier `data\network`.
- Utiliser HTTPS ou un reverse proxy interne si des postes distants saisissent des identifiants.
