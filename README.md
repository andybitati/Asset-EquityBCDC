# Assets Equity BCDC

Assets Equity BCDC est une application web de gestion de stock des matériels informatiques de la Banque Equity BCDC.

Elle permet de suivre les entrées et sorties de matériels comme les écrans, laptops, desktops, souris, switchs, routeurs, claviers et autres équipements. Chaque mouvement est horodaté et lié à l’utilisateur qui l’a initié. Les entrées conservent surtout le type, la quantité et la description, tandis que les sorties conservent aussi les informations détaillées de matériel, de destination et de bénéficiaire.

## Objectif

L’application répond à trois besoins principaux :

- connaître le stock réel disponible par type de matériel ;
- suivre l’historique complet des mouvements de chaque matériel ;
- anticiper les ruptures de stock grâce à des seuils calculés automatiquement.

## Architecture

- Backend : Python, FastAPI, SQLAlchemy
- Frontend : React, Vite, Recharts
- Base de données : MySQL, avec fallback SQLite si `DATABASE_URL` n’est pas défini
- Temps réel : WebSocket pour rafraîchir le stock et les indicateurs

## Modèle de données

La base contient les tables principales suivantes :

- `users` : utilisateurs autorisés à se connecter ;
- `equipment_types` : référentiel des types de matériels ;
- `materials` : référentiel des matériels enregistrés ;
- `movements` : journal des entrées et sorties.

### `materials`

La table `materials` représente le matériel lui-même :

- type de matériel ;
- numéro de série lorsque l’équipement est identifié précisément à la sortie ;
- modèle lorsque l’équipement est identifié précisément à la sortie ;
- description ;
- dates de création et de mise à jour.

Le stock courant n’est pas stocké directement dans cette table. Il est calculé à partir des mouvements afin d’éviter les désynchronisations.

### `movements`

La table `movements` contient le journal complet :

- matériel concerné (`material_id`) ;
- type de mouvement : entrée ou sortie ;
- quantité ;
- destination ;
- personne qui a pris le matériel ;
- utilisateur qui a initié le mouvement ;
- description ou note ;
- date et heure du mouvement.

## Règles métier

### Entrée de matériel

Une entrée ajoute du matériel au stock.

À l’entrée, l’utilisateur renseigne uniquement le type de matériel, la quantité et une description ou note si nécessaire. Le numéro de série, le modèle, la destination et la personne bénéficiaire ne sont pas exigés à ce stade.

Si le matériel n’existe pas encore dans `materials`, il est créé automatiquement comme matériel générique du type concerné, puis le mouvement d’entrée est enregistré.

### Sortie de matériel

Une sortie ne peut pas être saisie librement. Elle doit obligatoirement concerner un matériel déjà disponible en stock.

Pour chaque sortie, l’utilisateur doit renseigner :

- le matériel déjà présent en stock ;
- le numéro de série à sortir ;
- le modèle précis ;
- la destination du matériel ;
- la personne qui prend le matériel ;
- une description ou note de sortie si nécessaire.

Le système enregistre aussi automatiquement l’utilisateur connecté qui a initié le mouvement.

## Calcul du stock

Le stock disponible est calculé à partir du journal des mouvements.

Pour un matériel ou un type de matériel donné :

```text
stock_actuel = somme(entrées) - somme(sorties)
```

Exemple :

```text
Entrées Desktop = 10
Sorties Desktop = 3
Stock Desktop = 10 - 3 = 7
```

Cette méthode garantit que le stock affiché reste cohérent avec l’historique.

## Anticipation des commandes

L’application calcule automatiquement une métrique de consommation pour anticiper les commandes.

### Métrique retenue

La métrique principale est la consommation moyenne journalière sur les 90 derniers jours.

Pour chaque type de matériel :

```text
consommation_moyenne_journaliere = sorties_des_90_derniers_jours / 90
```

Exemple :

```text
Sorties Laptop sur 90 jours = 45
Consommation moyenne journalière = 45 / 90 = 0,5 Laptop par jour
```

L’application calcule aussi l’écart-type de la demande journalière sur cette même période.
Cet écart-type mesure la variabilité des sorties : plus les sorties sont irrégulières,
plus le stock de sécurité doit être élevé.

### Estimation du nombre de jours avant rupture

Si la consommation moyenne est supérieure à zéro :

```text
jours_avant_rupture = stock_actuel / consommation_moyenne_journaliere
```

Exemple :

```text
Stock Laptop = 6
Consommation moyenne journalière = 0,5
Jours avant rupture = 6 / 0,5 = 12 jours
```

Si aucune sortie n’a été observée sur les 90 derniers jours, l’application affiche `N/A`,
car il n’y a pas assez de consommation récente pour estimer une rupture.

## Seuils automatiques

L’application calcule les seuils par type de matériel à partir de paramètres visibles dans
l’écran `Politiques de stock` :

- délai fournisseur ;
- nombre de jours couverts par la réserve d’urgence ;
- stock minimum absolu ;
- couverture cible ;
- facteur de service.

Ces seuils ne sont pas arbitraires. Ils combinent la demande moyenne attendue et un stock
de sécurité lié à l’incertitude de la demande.

### Seuil de commande

Le seuil de commande indique à partir de quel niveau il faut envisager une nouvelle commande.

```text
demande_delai = consommation_moyenne_journaliere * delai_fournisseur
stock_securite_commande = ceil(facteur_service * ecart_type_demande * sqrt(delai_fournisseur))
seuil_commande = max(stock_minimum, ceil(demande_delai + stock_securite_commande))
```

Interprétation :

- `demande_delai` couvre la consommation moyenne prévue pendant l’attente fournisseur ;
- `stock_securite_commande` ajoute une marge contre les variations de la demande ;
- `max(stock_minimum, ...)` garantit un niveau minimal même si l’historique récent est faible.

Exemple :

```text
Consommation moyenne journalière = 0,5
Écart-type de la demande = 1
Délai fournisseur = 14 jours
Stock minimum = 2
Facteur de service = 1,28

Demande délai = 0,5 * 14 = 7
Stock sécurité commande = ceil(1,28 * 1 * sqrt(14)) = 5
Seuil commande = max(2, ceil(7 + 5))
Seuil commande = 12
```

Si le stock actuel est inférieur ou égal à ce seuil, le dashboard affiche un risque de pénurie.

### Réserve d’urgence

La réserve d’urgence protège un minimum de stock qui ne doit plus être utilisé pour les sorties normales.

```text
demande_urgence = consommation_moyenne_journaliere * jours_urgence
stock_securite_urgence = ceil(facteur_service * ecart_type_demande * sqrt(jours_urgence))
reserve_urgence = max(stock_minimum, ceil(demande_urgence + stock_securite_urgence))
```

Interprétation :

- `demande_urgence` couvre la consommation moyenne pendant la période d’urgence ;
- `stock_securite_urgence` protège contre les variations pendant cette période ;
- `max(stock_minimum, ...)` évite une réserve trop basse.

Exemple :

```text
Consommation moyenne journalière = 0,5
Écart-type de la demande = 1
Jours urgence = 5
Stock minimum = 2
Facteur de service = 1,28

Demande urgence = 0,5 * 5 = 2,5
Stock sécurité urgence = ceil(1,28 * 1 * sqrt(5)) = 3
Réserve urgence = max(2, ceil(2,5 + 3))
Réserve urgence = 6
```

### Facteur de service

Le facteur de service représente le niveau de prudence appliqué au stock de sécurité.
Il ne correspond pas à une quantité de matériel, mais à un nombre d’écarts-types ajoutés
au-dessus de la demande moyenne.

Dans les formules, il apparaît ainsi :

```text
stock_securite = facteur_service * ecart_type_demande * sqrt(nombre_de_jours)
```

L’échelle est exprimée en sigma :

```text
0,00 σ  = aucun stock de sécurité statistique
1,28 σ  ≈ niveau de service de 90 %
1,65 σ  ≈ niveau de service de 95 %
2,05 σ  ≈ niveau de service de 98 %
2,33 σ  ≈ niveau de service de 99 %
3,00 σ  ≈ niveau de service de 99,87 %
4,00 σ  ≈ niveau de service de 99,997 %
```

L’application accepte un facteur de service entre `0,00` et `4,00`.
Les valeurs par défaut sont :

```text
1,28 pour les matériels non sérialisés
1,65 pour les matériels sérialisés
```

Un facteur plus élevé réduit le risque de rupture, mais augmente le stock immobilisé.
Un facteur plus faible limite le stock dormant, mais augmente le risque de rupture.
Ce paramètre doit donc être choisi selon la criticité du matériel, son coût, son délai de
remplacement et l’impact métier d’une rupture.

La racine carrée est utilisée parce que l’incertitude ne s’additionne pas comme la demande
moyenne. Sur plusieurs jours, les moyennes s’additionnent directement :

```text
demande_moyenne_sur_n_jours = moyenne_journaliere * n
```

Mais pour la variabilité, ce sont les variances qui s’additionnent. Comme l’écart-type est
la racine carrée de la variance, l’incertitude totale devient :

```text
ecart_type_sur_n_jours = ecart_type_journalier * sqrt(n)
```

Cela évite de surestimer le risque comme si chaque jour défavorable s’accumulait toujours
dans le même sens.

### Contrôle des sorties proches de la réserve

Les seuils bas ne bloquent pas automatiquement la sortie. Quand le stock atteint la réserve
d’urgence ou qu’une sortie ferait passer le stock sous cette réserve, l’application demande
un avis responsable et trace l’opération dans l’audit.

Le contrôle utilisé est :

```text
stock_actuel <= reserve_urgence
```

ou :

```text
stock_actuel - quantite_demandee < reserve_urgence
```

## Dashboard

Le dashboard affiche :

- le stock total ;
- le total des entrées ;
- le total des sorties ;
- les types actifs en stock ;
- l’évolution du stock par type de matériel ;
- les risques de pénurie ;
- le seuil de commande ;
- la réserve d’urgence ;
- les mouvements récents filtrables.

La barre de recherche permet de retrouver un mouvement par :

- type de matériel ;
- numéro de série ;
- modèle ;
- destination ;
- personne qui a pris le matériel ;
- utilisateur qui a initié le mouvement ;
- description.

Le graphique d’évolution du stock affiche le stock net disponible dans le temps. Une entrée augmente la courbe du type concerné, une sortie la diminue. Le graphique ne sépare donc pas les entrées et les sorties : il montre le résultat final après chaque mouvement.

## Authentification

Chaque utilisateur doit se connecter avant d’accéder à l’application.

Les utilisateurs sont stockés dans la table `users`. Cette table contient notamment :

- l’identifiant de connexion ;
- le nom affiché ;
- le hash du mot de passe ;
- le rôle ;
- l’URL ou le chemin de la photo utilisateur (`photo_url`) ;
- le statut actif/inactif.

Lorsqu’un mouvement est créé, le backend associe automatiquement le mouvement à l’utilisateur connecté via le champ `initiated_by`.

### Règle de mot de passe

Un mot de passe valide doit respecter toutes les conditions suivantes :

- au moins 8 caractères ;
- au moins une lettre majuscule ;
- au moins un chiffre ;
- au moins un caractère spécial.

Exemple valide :

```text
StrongPassword123!
```

Exemple invalide :

```text
password
```

## Configuration MySQL

Le backend utilise la variable `DATABASE_URL` définie dans `backend/.env`.

Exemple :

```env
DATABASE_URL=mysql+pymysql://asset_equity_user:ChangeMe123!@127.0.0.1:3306/asset_equity
```

Le script de création de base se trouve ici :

```text
backend/mysql-init.sql
```

Il crée :

- la base `asset_equity` ;
- l’utilisateur MySQL applicatif ;
- les tables nécessaires ;
- les types de matériels initiaux ;
- les utilisateurs initiaux.

## Installation

Depuis la racine du projet :

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
npm install
npm --prefix frontend install
```

## Lancement

Le lancement recommandé se fait avec :

```powershell
.\start-all.bat
```

Cela démarre :

- le backend sur `http://localhost:48620` ;
- le frontend sur `http://localhost:48621` ;
- le navigateur vers l’interface web.

Un raccourci Bureau peut être créé avec :

```powershell
powershell -ExecutionPolicy Bypass -File scripts\CreateDesktopShortcut.ps1
```

## Connexion MySQL en production

La procédure complète de connexion à une base MySQL de production est documentée ici :

```text
docs/PRODUCTION_DB_SETUP.md
```

Résumé :

- ouvrir MySQL Workbench sur la machine cible ou le serveur DB ;
- exécuter `backend/mysql-init.sql` ;
- créer ou vérifier `backend/.env` ;
- renseigner `DATABASE_URL` ;
- lancer le backend pour vérifier la connexion ;
- démarrer l’application.

## Installateur Windows `.exe`

Un vrai installateur Windows peut être généré avec Inno Setup à partir de :

```text
installer/AssetsEquityBCDC.iss
```

Cet installateur :

- copie l’application dans `C:\Program Files\Assets Equity BCDC` ;
- crée les raccourcis ;
- lance `scripts/InstallDependencies.ps1` ;
- prépare le venv Python ;
- installe les dépendances backend et frontend.

Pré-requis sur la machine installée :

- Python 3.11+ ;
- Node.js LTS ;
- accès à MySQL ;
- accès réseau interne si la base est distante.

Pour construire le setup :

```powershell
iscc installer\AssetsEquityBCDC.iss
```

Le résultat attendu est :

```text
installer\AssetsEquityBCDC-Setup.exe
```

La documentation détaillée de l’installateur est disponible ici :

```text
docs/WINDOWS_INSTALLER.md
```

## Développement

Backend seul :

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 48620
```

Frontend seul :

```powershell
npm --prefix frontend run dev
```

Build frontend :

```powershell
npm --prefix frontend run build
```

## Politiques de sécurité bancaires

Assets Equity BCDC traite des données internes de stock informatique d’une banque. Même si ces données ne sont pas directement des données financières client, elles restent sensibles parce qu’elles décrivent les équipements, les mouvements internes, les utilisateurs, les destinations et les responsabilités opérationnelles.

Cette section décrit les politiques de sécurité attendues pour une mise en production dans un environnement bancaire.

### Classification des données

Les données de l’application doivent être considérées comme confidentielles internes.

Sont notamment sensibles :

- les comptes utilisateurs ;
- les photos et profils utilisateurs ;
- les mouvements de matériels ;
- les numéros de série ;
- les destinations internes ;
- les personnes ayant pris un matériel ;
- les utilisateurs ayant initié les opérations ;
- les statistiques de stock et de pénurie.

Ces informations ne doivent pas être exposées publiquement, copiées dans des fichiers non sécurisés ou partagées hors des canaux internes autorisés.

### Authentification

Chaque utilisateur doit disposer d’un compte nominatif. Les comptes partagés sont interdits.

Politique minimale :

- connexion obligatoire avant toute consultation ;
- mot de passe d’au moins 8 caractères ;
- au moins une majuscule ;
- au moins un chiffre ;
- au moins un caractère spécial ;
- blocage ou surveillance des tentatives de connexion répétées ;
- désactivation immédiate des comptes des utilisateurs sortants ;
- interdiction d’utiliser des mots de passe par défaut en production.

Politique recommandée pour production bancaire :

- hachage des mots de passe avec Argon2id ou bcrypt ;
- rotation périodique selon la politique interne de la banque ;
- authentification multifacteur pour les administrateurs ;
- expiration automatique des sessions ;
- révocation serveur des sessions compromises.

### Gestion des identifiants

Les utilisateurs peuvent modifier leurs identifiants et leur photo depuis l’interface, mais pas librement à tout moment.

Règle métier appliquée :

```text
Un utilisateur standard ne peut modifier ses identifiants qu’une fois tous les 3 mois.
```

Exception :

```text
L’administrateur peut modifier les identifiants à tout moment.
```

Restriction importante :

```text
L’administrateur ne peut jamais modifier le mot de passe d’un autre utilisateur.
```

L’administrateur peut :

- modifier l’identifiant ;
- modifier le nom affiché ;
- modifier le rôle ;
- modifier la photo ;
- activer ou désactiver un compte ;
- supprimer un compte.

Il ne peut pas :

- connaître le mot de passe d’un utilisateur ;
- remplacer directement le mot de passe d’un utilisateur.

Si un utilisateur perd son mot de passe, la procédure recommandée est une réinitialisation contrôlée via un processus séparé, journalisé et validé par l’équipe habilitée.

### Photos de profil

Les photos de profil peuvent être choisies parmi les avatars proposés ou chargées depuis
un fichier local.

Règles appliquées :

- formats acceptés : JPG, PNG, WEBP ou GIF ;
- taille maximale enregistrée : `2 Mo` ;
- si la photo chargée dépasse `2 Mo`, l’interface tente de la redimensionner et de la
  compresser automatiquement avant l’envoi ;
- si la photo reste trop lourde après compression, l’utilisateur doit choisir une image
  plus petite.
- pour un utilisateur existant, la photo chargée est immédiatement enregistrée dans la
  base de données ;
- lors de la création d’un nouvel utilisateur, la photo est préparée puis enregistrée avec
  le compte au moment de la création.

L’affichage des photos est prévu pour recadrer proprement les images dans un espace fixe,
afin d’éviter les déformations ou les débordements dans le menu, le profil et les tableaux
utilisateurs.

### Autorisations et séparation des rôles

Le principe du moindre privilège doit être appliqué.

Rôles recommandés :

- `admin` : gestion des utilisateurs, supervision, configuration ;
- `user` : saisie des entrées/sorties et consultation opérationnelle ;
- `auditor` : consultation seule, sans entrée, sortie, import, export ni modification ;
- `manager` : consultation des alertes, validations, rapports et actions opérationnelles autorisées.

Une action sensible doit être réservée aux rôles nécessaires uniquement.

Actions sensibles :

- suppression d’un utilisateur ;
- désactivation d’un compte ;
- modification des identifiants ;
- export des données ;
- suppression ou correction de mouvements ;
- modification des paramètres de seuils ;
- accès aux rapports globaux.

### Traçabilité et audit

Chaque mouvement doit permettre de répondre aux questions suivantes :

- quel matériel est concerné ?
- quel type de mouvement a été effectué ?
- quelle quantité a été déplacée ?
- quand le mouvement a-t-il eu lieu ?
- où va le matériel ?
- qui l’a pris ?
- quel utilisateur a initié l’opération ?

Le champ `initiated_by` permet d’identifier l’utilisateur connecté qui a enregistré l’opération.

Pour une production bancaire, il faut aller plus loin avec une table d’audit dédiée.

Exemple de table recommandée :

```text
audit_logs
- id
- actor_username
- action
- entity_type
- entity_id
- old_value
- new_value
- ip_address
- user_agent
- created_at
```

Les logs d’audit doivent être :

- non modifiables par les utilisateurs applicatifs ;
- conservés selon la durée réglementaire interne ;
- consultables uniquement par les profils autorisés ;
- exportables pour contrôle interne ou audit de sécurité.

### Confidentialité et chiffrement

Toutes les communications doivent être chiffrées en production.

Obligatoire :

- HTTPS/TLS entre navigateur et backend ;
- TLS entre backend et base MySQL si la base est distante ;
- cookies ou tokens protégés ;
- interdiction de transmettre des secrets dans l’URL ;
- désactivation des logs contenant mots de passe, tokens ou secrets.

Recommandé :

- chiffrement au repos du serveur MySQL ;
- chiffrement des sauvegardes ;
- gestion des clés via un coffre de secrets ;
- rotation des secrets applicatifs.

### Gestion des secrets

Les secrets ne doivent jamais être commités dans Git.

Sont considérés comme secrets :

- mots de passe MySQL ;
- clés applicatives ;
- tokens ;
- identifiants administrateurs ;
- chaînes de connexion ;
- certificats privés.

La configuration doit passer par :

- `.env` local non versionné ;
- variables d’environnement serveur ;
- coffre de secrets en production.

Le fichier `.env` ne doit jamais être transmis par messagerie non sécurisée.

### Sécurité base de données

Le compte MySQL utilisé par l’application doit avoir uniquement les privilèges nécessaires.

Politique minimale :

- compte applicatif séparé du compte `root` ;
- mot de passe fort ;
- accès limité à la base `asset_equity` ;
- interdiction d’utiliser `root` depuis l’application ;
- sauvegardes régulières ;
- restauration testée périodiquement.

Recommandé :

- chiffrement des sauvegardes ;
- compte lecture seule pour reporting/audit ;
- journalisation des accès administrateurs ;
- segmentation réseau entre application et base ;
- restrictions par adresse IP ou réseau interne.

### Sécurité réseau

L’application doit fonctionner uniquement sur le réseau autorisé de la banque.

En production :

- ne pas exposer le backend directement sur Internet ;
- placer l’application derrière un reverse proxy sécurisé ;
- limiter les ports ouverts ;
- utiliser un pare-feu ;
- journaliser les accès ;
- séparer les environnements développement, test et production.

### Protection contre les erreurs de manipulation

Certaines opérations doivent être protégées par des confirmations ou restrictions.

Exemples :

- suppression utilisateur ;
- désactivation utilisateur ;
- export de données ;
- modification des identifiants ;
- mouvements de sortie importants ;
- sorties proches de la réserve d’urgence.

Les sorties proches de la réserve d’urgence sont contrôlées par l’application.
Elles demandent un avis responsable et sont tracées dans l’audit.

Rappel :

```text
Si stock_actuel <= reserve_urgence, un avis responsable est requis.
```

Et :

```text
Si stock_actuel - quantite_demandee < reserve_urgence, un avis responsable est requis.
```

### Sauvegarde et restauration

Une politique de sauvegarde est obligatoire.

Minimum recommandé :

- sauvegarde quotidienne de MySQL ;
- sauvegarde avant toute migration ;
- conservation sur plusieurs jours ;
- stockage sécurisé ;
- restauration testée régulièrement.

Les sauvegardes doivent inclure :

- tables applicatives ;
- utilisateurs ;
- mouvements ;
- matériels ;
- logs d’audit si présents.

Les sauvegardes ne doivent pas être laissées en clair dans le dossier projet.

### Journalisation applicative

Les logs doivent aider au diagnostic sans exposer de secrets.

À journaliser :

- erreurs backend ;
- tentatives de connexion échouées ;
- opérations administrateur ;
- erreurs de base de données ;
- refus de sorties pour réserve d’urgence.

À ne jamais journaliser :

- mots de passe ;
- hashes de mots de passe ;
- tokens de session ;
- chaînes de connexion complètes ;
- secrets applicatifs.

L’application prévoit deux fichiers de logs locaux :

```text
backend/logs/app.log
backend/logs/security.log
```

`app.log` sert aux événements applicatifs généraux.

`security.log` sert aux événements sensibles :

- connexions réussies ;
- connexions échouées ;
- déconnexions ;
- exports ;
- modifications utilisateurs ;
- suppressions utilisateurs ;
- entrées/sorties de stock.

Les logs utilisent une rotation automatique. Les paramètres configurables sont :

```env
LOG_DIR=backend/logs
LOG_LEVEL=INFO
LOG_MAX_BYTES=5242880
LOG_BACKUP_COUNT=5
```

Le dossier `backend/logs/` est ignoré par Git.

### Environnements

Les environnements doivent être séparés.

```text
développement != test != production
```

Chaque environnement doit avoir :

- sa propre base ;
- ses propres utilisateurs ;
- ses propres secrets ;
- ses propres règles de sauvegarde ;
- ses propres accès réseau.

Les données de production ne doivent pas être copiées en développement sans anonymisation ou autorisation formelle.

### Durcissement avant production

Le code intègre déjà plusieurs mesures applicatives :

- hachage PBKDF2-SHA256 avec sel ;
- migration automatique des anciens hashes SHA-256 au prochain login ;
- expiration des sessions ;
- limitation des tentatives de connexion ;
- table `audit_logs` ;
- rôles `admin`, `user`, `manager`, `auditor` ;
- export CSV protégé par authentification et rôle ;
- journalisation des entrées, sorties, exports et changements utilisateurs ;
- script de sauvegarde MySQL : `scripts/BackupMySql.ps1`.

Avant une mise en production bancaire complète, les points suivants restent à traiter dans l’infrastructure ou par procédure :

- ajouter authentification multifacteur pour les administrateurs ;
- imposer HTTPS ;
- sécuriser les sauvegardes ;
- documenter une procédure de restauration ;
- documenter une procédure de révocation d’accès ;
- faire une revue de code sécurité ;
- faire un test d’intrusion interne ou externe selon la politique de la banque.
