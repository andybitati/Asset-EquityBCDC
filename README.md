# Assets EquityBCDC

Projet de logiciel web de gestion de stock pour équipements informatiques.

## Architecture

- backend: Python + FastAPI
- frontend: React + Vite

## Fonctionnalités

- Authentification obligatoire
- Suivi des entrées/sorties de matériel
- Stock en temps réel via WebSocket
- CSV log automatique en arrière-plan
- Export CSV à la demande
- Dashboard de suivi et prévision de commande

## Démarrage

### Installation

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd ..
npm install
```

### Lancer les deux serveurs ensemble

Depuis la racine du projet (`F:\Asset-Equity`) :

```powershell
npm run dev
```

Cela démarre :
- le backend FastAPI sur `http://localhost:8000`
- le frontend React sur `http://localhost:5173`

### Lancer séparément

Si nécessaire, tu peux aussi lancer séparément :

Backend :
```powershell
cd backend
venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend :
```powershell
cd frontend
npm install
npm run dev
```

### Lancer d’un seul clic

J’ai ajouté un script racine `start-all.bat` dans `F:\Asset-Equity`.

Pour lancer le backend et le frontend ensemble :

```powershell
cd F:\Asset-Equity
start-all.bat
```

### Créer un raccourci bureau

1. Ouvre l’Explorateur Windows.
2. Va dans `F:\Asset-Equity`.
3. Clique droit sur `start-all.bat` puis `Envoyer vers > Bureau (créer un raccourci)`.
4. Double-clique sur le raccourci bureau pour démarrer les deux serveurs.

```powershell
cd frontend
npm install
npm run dev
```

## Notes

Le backend expose une API avec WebSocket pour les mises à jour en temps réel. Le frontend React consomme ces données et affiche des graphiques.
