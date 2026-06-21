# Installateur Windows

Le projet contient un script Inno Setup :

```text
installer/AssetsEquityBCDC.iss
```

Il permet de générer :

```text
AssetsEquityBCDC-Setup.exe
```

## Ce que fait l’installateur

- copie l’application dans `C:\Program Files\Assets Equity BCDC` ;
- crée les raccourcis Bureau et menu Démarrer ;
- lance `scripts/InstallDependencies.ps1` ;
- prépare le virtualenv Python ;
- installe les dépendances Python ;
- installe les dépendances Node/frontend.

## Prérequis de la version actuelle

La version actuelle suppose que la machine possède déjà :

- Python 3.11+ ;
- Node.js LTS ;
- npm ;
- accès réseau ou dépôt interne pour installer les dépendances ;
- accès à la base MySQL.

## Version bancaire recommandée

Pour une banque, il est préférable d’éviter les téléchargements directs depuis Internet pendant l’installation.

La version recommandée de l’installateur devrait embarquer :

- un runtime Python validé ;
- Node.js ou un build frontend déjà compilé ;
- les wheels Python hors ligne ;
- les packages npm hors ligne ou le dossier frontend buildé ;
- un fichier `.env.example` ;
- une procédure de configuration DB.

Dans cette approche, l’installation ne dépend pas d’Internet et reste reproductible.

## Compilation

Installer Inno Setup sur la machine de build, puis exécuter :

```powershell
iscc installer\AssetsEquityBCDC.iss
```

Le fichier généré sera placé dans :

```text
installer\AssetsEquityBCDC-Setup.exe
```

## Après installation

1. Ouvrir MySQL Workbench.
2. Exécuter `backend/mysql-init.sql` si la base n’existe pas.
3. Configurer `backend/.env`.
4. Lancer le raccourci `Assets Equity BCDC`.

La procédure DB complète est dans :

```text
docs/PRODUCTION_DB_SETUP.md
```
