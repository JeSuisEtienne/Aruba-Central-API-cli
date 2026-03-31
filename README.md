# Aruba Central API Report

Outil Python de génération de rapports Excel depuis l'API Aruba Central.
Collecte l'inventaire des équipements réseau, le statut firmware des switches, gateways et points d'accès, avec calcul automatique des versions maximales disponibles par branche. Supporte une architecture multi-clients avec configurations et tokens isolés.

Disponible en **deux modes** : interface web Streamlit (`app.py`) ou scripts en ligne de commande (`main.py` / `main_mrt.py`).

---

## Table des matières

1. [Fonctionnalités](#fonctionnalités)
2. [Prérequis](#prérequis)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Interface web Streamlit](#interface-web-streamlit)
6. [Utilisation en ligne de commande](#utilisation-en-ligne-de-commande)
7. [Rapports générés](#rapports-générés)
8. [Rapports MRT](#rapports-mrt)
9. [Structure du projet](#structure-du-projet)
10. [Architecture technique](#architecture-technique)
11. [Bonnes pratiques](#bonnes-pratiques)
12. [Dépannage](#dépannage)

---

## Fonctionnalités

- **Interface web Streamlit** : application multi-pages avec sélection de client, génération en temps réel, aperçu des données et téléchargement Excel directement dans le navigateur
- **Rapport Excel multi-feuilles** : inventaire, firmware switches, firmware swarms, gateways, vue consolidée
- **Calcul automatique de `firmware_max`** : détecte la version maximale disponible dans la même branche de version
- **Multi-clients** : chaque client a sa propre configuration et ses propres tokens — aucun conflit possible
- **Détection automatique des clients** : scan du dossier `.env/` sans configuration manuelle
- **Création de rapports MRT** : planification de rapports dans New Central via OAuth2 HPE SSO, avec filtrage par site et récurrence
- **Notifications email** : envoi optionnel du rapport par email via SMTP

---

## Prérequis

- **Python 3.9+**
- Accès à l'API Aruba Central : `client_id`, `client_secret`, `customer_id`, `base_url`
- Un compte Aruba Central avec les permissions API nécessaires
- Excel ou un lecteur de fichiers `.xlsx` pour consulter le rapport

---

## Installation

### Option 1 — Script automatique (Windows PowerShell)

```powershell
.\install.ps1
```

Le script vérifie Python 3.9+, met à jour pip, et installe toutes les dépendances.

### Option 2 — Installation manuelle

```bash
pip install -r requirements.txt
```

### Option 3 — Installation minimale

```bash
pip install arubacentral requests pandas openpyxl python-dotenv
```

Pour l'**interface Streamlit** :

```bash
pip install streamlit
```

Pour les **rapports MRT** :

```bash
pip install oauthlib requests-oauthlib
```

> **Note sur `pycentral`** : Le package PyPI (`arubacentral`) expose `ArubaCentralBase` via `from pycentral.base import ArubaCentralBase`. L'ancienne structure `pycentral.classic.base` n'est plus utilisée.

---

## Configuration

### Structure des fichiers de configuration

```
Script Central/
├── auth.env                  # Identifiants partagés (username/password)
└── .env/
    ├── Client1.env           # Configuration du client 1
    ├── Client2.env           # Configuration du client 2
    └── ...                   # Un fichier .env par client/site
```

### 1. Fichier `auth.env` — identifiants partagés

Créez `Script Central/auth.env` avec vos identifiants Aruba Central :

```env
CENTRAL_USERNAME=votre_username
CENTRAL_PASSWORD=votre_password
```

Ce fichier est chargé pour tous les clients. Il ne contient **pas** les informations spécifiques à un client.

### 2. Fichiers clients dans `.env/`

Créez un fichier `.env` par client dans le dossier `Script Central/.env/`. Le nom du fichier (sans l'extension) devient le nom du client dans le menu de sélection.

**Exemple : `Script Central/.env/Client1.env`**

```env
CLIENT_ID=votre_client_id
CLIENT_SECRET=votre_client_secret
CUSTOMER_ID=votre_customer_id
BASE_URL=https://apigw-eucentral3.central.arubanetworks.com
```

**Variables disponibles dans un fichier client :**

| Variable | Obligatoire | Description |
|---|---|---|
| `CLIENT_ID` | Oui | ID de l'application API Aruba Central |
| `CLIENT_SECRET` | Oui | Secret de l'application API |
| `CUSTOMER_ID` | Oui | ID du tenant client |
| `BASE_URL` | Oui | URL de la passerelle API selon la région |
| `SMTP_SERVER` | Non | Serveur SMTP pour l'envoi par email |
| `SMTP_PORT` | Non | Port SMTP (ex: 587) |
| `EMAIL_FROM` | Non | Adresse expéditeur |
| `EMAIL_TO` | Non | Adresse(s) destinataire(s) |

### Régions et BASE_URL

| Région | BASE_URL |
|---|---|
| EU Central 3 | `https://apigw-eucentral3.central.arubanetworks.com` |
| EU | `https://eu-apigw.central.arubanetworks.com` |
| US West | `https://apigw-uswest.central.arubanetworks.com` |
| US East | `https://apigw-useast.central.arubanetworks.com` |
| AP (Asie-Pacifique) | `https://apigw-apj.central.arubanetworks.com` |

> Vérifiez la région de votre tenant dans les paramètres de votre compte Aruba Central.

---

## Interface web Streamlit

L'interface Streamlit est le mode d'utilisation recommandé. Elle offre une expérience graphique dans le navigateur sans ligne de commande.

### Lancement

```bash
streamlit run "Script Central/app.py"
```

Streamlit ouvre automatiquement l'application dans votre navigateur (par défaut : `http://localhost:8501`).

### Page 1 — Firmware & Inventaire (`app.py`)

La page principale permet de générer le rapport Excel complet.

**Fonctionnement :**

1. **Sélection du client** via un menu déroulant (clients auto-détectés depuis `.env/`)
2. **Clic sur "Générer le rapport"** — la progression s'affiche en temps réel :
   - Chargement de la configuration
   - Connexion à Aruba Central
   - Collecte des données (inventaire, switches, gateways, firmware…)
   - Génération du fichier Excel en mémoire
3. **Métriques résumées** : nombre de lignes par feuille (Firmware Consolidé, Inventaire, Switches, Gateways, Firmware Switch, Firmware Swarms)
4. **Téléchargement direct** du fichier `.xlsx` nommé `<Client>_<date>.xlsx`
5. **Aperçu des données** dans des onglets interactifs avec tableau paginable pour chaque feuille

> Le rapport est généré en mémoire — aucun fichier n'est écrit sur le disque serveur.

**Gestion des erreurs :** les erreurs d'authentification (401, identifiants incorrects) sont affichées directement dans l'interface avec les causes fréquentes et les actions correctives.

---

### Page 2 — Création de Rapport MRT (`pages/Rapport_MRT.py`)

Accessible depuis la barre latérale, cette page permet de créer des rapports MRT planifiés directement dans New Central.

**Formulaire en 6 étapes :**

| Étape | Description |
|---|---|
| 1. Client | Sélection du client Aruba Central |
| 2. Type | Type de rapport (Inventory, Client Session, RF Health, Network Usage…) |
| 3. Période | Dernier jour / semaine / mois ou plage personnalisée |
| 4. Planification | Une seule fois, quotidien, hebdomadaire ou mensuel (avec dates de début/fin) |
| 5. Périmètre | Global, tous les sites, ou un site spécifique |
| 6. Récapitulatif | Résumé de la configuration avant création |

**Types de rapports disponibles :**

| Clé API | Libellé |
|---|---|
| `inventory` | Inventory — Liste des équipements |
| `clientInventory` | Client Inventory — Inventaire des clients |
| `clientSession` | Client Session — Sessions clients |
| `appAnalytics` | Application Analytics |
| `deviceUptime` | Device Uptime |
| `networkUsage` | Network Usage |
| `resourceUtilization` | Resource Utilization |
| `capacityPlanning` | Capacity Planning |
| `rfHealth` | RF Health |
| `custom` | Custom — Rapport personnalisé |

**Périmètre :**
- **Global** : un seul rapport global pour le tenant
- **Tous les sites** : un rapport créé automatiquement pour chaque site (barre de progression)
- **Site spécifique** : choix dans une liste chargée depuis l'API

Une fois créé, le rapport apparaît dans l'interface Aruba Central (New Central) avec son ID et son nom.

---

## Utilisation en ligne de commande

### Rapport principal (inventaire + firmware)

```bash
python "Script Central/main.py"
```

Le script affiche un menu interactif pour choisir le client, puis génère automatiquement le rapport Excel dans `Script Central/Report/<NomClient>.xlsx`.

**Exemple de session :**

```
Clients disponibles :
  1. Client1
  2. Client2
  3. Hermite
Sélectionnez un client [1-3] : 2

✅ Configuration chargée pour Client2
🔗 Connexion à https://apigw-eucentral3.central.arubanetworks.com
📊 Collecte des données en cours...
✅ Rapport généré : Report/Client2.xlsx
```

### Rapport MRT

```bash
python "Script Central/main_mrt.py"
```

Le script demande le client, le type de rapport, et la période, puis génère un fichier Excel avec les rapports disponibles.

---

## Rapports générés

### Rapport principal (`Report/<Client>.xlsx`)

Le fichier Excel contient les feuilles suivantes, dans cet ordre :

#### 1. Firmware Consolidé *(première feuille)*

Vue unifiée de tous les équipements managés : switches, Virtual Controllers et gateways.

| Colonne | Description |
|---|---|
| `serial` | Numéro de série |
| `mac_address` | Adresse MAC |
| `hostname` | Nom de l'équipement |
| `model` | Modèle |
| `firmware_version` | Version firmware actuelle |
| `recommended` | Version recommandée par Aruba |
| `firmware_max` | Version maximale disponible dans la même branche |

#### 2. Inventaire

Liste complète de tous les équipements du tenant, telle que retournée par l'API.

#### 3. Switches (Stack)

Switches récupérés depuis `monitoring/v1/switches`. Inclut les informations de stack :

| Colonne | Description |
|---|---|
| `stack_status` | Statut stack (standalone, master, member…) |
| `stack_id` | Identifiant de la stack |
| `stack_role` | Rôle dans la stack |
| `stack_member_id` | ID du membre dans la stack |

#### 4. Firmware Switch

Détails firmware pour les switches HP (2930F) et CX (6300) via `firmware/v1/devices`. La colonne `firmware_max` est calculée automatiquement.

#### 5. Gateways

Liste des gateways avec leur version recommandée récupérée individuellement via `/monitoring/v1/gateways/{serial}`. Calcul de `firmware_max` avec gestion du format spécial de version gateway (ex: `8.7.0.0-2.3.0.9`).

#### 6. Firmware Swarms

Virtual Controllers (VC) et tous les points d'accès associés. Calcul de `firmware_max` dans la même branche majeure/mineure (ex : `8.13.x.x`).

### Calcul de `firmware_max`

Le script détermine pour chaque équipement la version de firmware la plus récente disponible **dans la même branche** que la version actuelle :

| Type d'équipement | Logique de branche |
|---|---|
| IAP / VC | Même `major.minor` (ex: `8.13.x.x`) |
| Switches 2930F | Versions HP disponibles, même branche |
| Switches 6300 | Versions CX disponibles, même branche |
| Gateways | Format `A.B.C.D-E.F.G.H` — comparaison des deux parties |

Si aucune version supérieure n'existe dans la branche, `firmware_max` est vide.

---

## Rapports MRT

Les rapports MRT (Monitoring, Reports & Troubleshooting) utilisent une authentification OAuth2 distincte via **HPE SSO**, différente des autres scripts.

### Authentification OAuth2 pour New Central

- **URL du token** : `https://sso.common.cloud.hpe.com/as/token.oauth2`
- **Grant type** : `client_credentials`
- **Librairie** : `BackendApplicationClient` + `OAuth2Session` de `requests_oauthlib`

L'authentification est effectuée à chaque session (pas de cache de token côté MRT).

### Endpoints API utilisés

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/reports/api/v1/{customer_id}/generated` | Liste des rapports générés |
| `GET` | `/reports/api/v1/{customer_id}/scheduled` | Liste des rapports programmés |
| `GET` | `/reports/api/v1/{customer_id}/generated/{report_id}` | Détails d'un rapport |

### Rapport MRT Excel

Le fichier généré contient deux feuilles :

- **Rapports Générés** : ID, type, date, statut, paramètres, URL de téléchargement
- **Rapports Programmés** : ID, nom, configuration de planification, paramètres

---

## Structure du projet

```
Aruba-Central-API/
├── README.md
├── .gitignore
└── Script Central/
    │
    ├── auth.env                        # Identifiants partagés (non versionné)
    ├── .env/                           # Configurations clients (non versionnées)
    │   ├── Client1.env
    │   └── Client2.env
    ├── temp/                           # Tokens isolés par client (non versionnés)
    │   ├── Client1/
    │   │   └── tok_*.json
    │   └── Client2/
    │       └── tok_*.json
    ├── Report/                         # Rapports Excel générés
    │   ├── Client1.xlsx
    │   └── Client2.xlsx
    │
    ├── app.py                          # Interface Streamlit — page Firmware & Inventaire
    ├── pages/
    │   └── Rapport_MRT.py             # Interface Streamlit — page création MRT
    │
    ├── main.py                         # Point d'entrée CLI — rapport principal
    ├── main_mrt.py                     # Point d'entrée CLI — rapports MRT
    │
    ├── central_config.py               # Chargement des configurations clients
    ├── clients_config.py               # Détection automatique des clients
    ├── data_pipeline.py                # Orchestration de la collecte de données
    │
    ├── script_inventaire.py            # Récupération de l'inventaire
    ├── script_firmware_switch.py       # Firmware des switches (HP/CX)
    ├── script_firmware_swarms.py       # Firmware des swarms (VC + APs)
    ├── script_firmware_versions.py     # Versions firmware disponibles + comparaison
    ├── script_list_switches.py         # Liste des switches avec info stack
    ├── script_list_gateways.py         # Liste des gateways + versions recommandées
    ├── script_load_token.py            # Chargement et gestion des tokens
    ├── script_mrt_reports.py           # Appels API MRT
    │
    ├── excel_export.py                 # Génération du fichier Excel
    ├── excel_format.py                 # Mise en forme du fichier Excel
    └── email_sender.py                 # Envoi optionnel par email
```

---

## Architecture technique

### Flux d'exécution

**Mode Streamlit (recommandé)**
```
streamlit run app.py
  │
  ├── [Page 1] app.py
  │     ├── clients_config / central_config  → Sélection client
  │     ├── data_pipeline.py                 → Collecte des données
  │     └── excel_export.export_to_excel_buffer()  → Excel en mémoire → téléchargement
  │
  └── [Page 2] pages/Rapport_MRT.py
        ├── central_config               → Sélection client
        ├── script_mrt_reports.lister_sites()       → API sites
        └── script_mrt_reports.creer_rapport_programme()  → API New Central
```

**Mode CLI**
```
main.py
  │
  ├── clients_config.py        → Scan de .env/ → liste des clients
  ├── central_config.py        → Chargement auth.env + <client>.env
  │
  └── data_pipeline.py         → Orchestration
        ├── script_inventaire.py
        ├── script_list_switches.py
        ├── script_firmware_switch.py
        ├── script_list_gateways.py
        ├── script_firmware_swarms.py
        └── script_firmware_versions.py  → Calcul firmware_max
              │
              └── excel_export.py + excel_format.py → .xlsx
```

### Gestion des tokens

Chaque client dispose de son propre dossier de tokens :

```
temp/
├── Client1/        ← CENTRAL_TOKEN_DIR pour Client1
│   └── tok_*.json
└── Client2/        ← CENTRAL_TOKEN_DIR pour Client2
    └── tok_*.json
```

La variable d'environnement `CENTRAL_TOKEN_DIR` est définie dynamiquement à chaque exécution selon le client sélectionné. Le SDK `ArubaCentralBase` gère le rafraîchissement automatique des tokens.

**Réinitialiser un token :**

```bash
rm -rf "Script Central/temp/<NomClient>/"
```

### Endpoints API utilisés (rapport principal)

| Endpoint | Description |
|---|---|
| `/firmware/v1/devices` | Statut firmware des switches |
| `/firmware/v1/versions` | Versions firmware disponibles |
| `/firmware/v1/swarms` | Firmware Virtual Controllers et APs |
| `/monitoring/v1/switches` | Inventaire switches avec info stack |
| `/monitoring/v1/gateways` | Liste paginée des gateways |
| `/monitoring/v1/gateways/{serial}` | Détails et version recommandée par gateway |
| `/monitoring/v2/aps` | Détails APs (site, IP) |

---

## Bonnes pratiques

- **Ne versionnez jamais** `auth.env`, les fichiers `.env/`, ni le dossier `temp/` — ajoutez-les au `.gitignore`
- **Vérifiez la `BASE_URL`** dans chaque fichier client : elle doit correspondre à la région de votre tenant
- **Utilisez un environnement virtuel** pour isoler les dépendances Python du projet
- **Un fichier `.env` = un client** : nommez-le de façon explicite, ce nom apparaît dans le menu
- **Supprimez `temp/<client>/`** si vous changez de `BASE_URL` ou rencontrez des erreurs 401

---

## Dépannage

### Erreur 401 — Token invalide ou expiré

**Cause** : token généré avec une `BASE_URL` différente, ou token expiré.

**Solution** :
```bash
rm -rf "Script Central/temp/<NomClient>/"
```
Puis relancez le script — un nouveau token sera généré automatiquement.

---

### "Aucun client n'est configuré"

**Cause** : le dossier `.env/` est absent ou vide.

**Solution** : créez `Script Central/.env/` et ajoutez au moins un fichier `<Client>.env`.

---

### "Le fichier auth.env principal est introuvable"

**Solution** : créez `Script Central/auth.env` avec les variables `CENTRAL_USERNAME` et `CENTRAL_PASSWORD`.

---

### "La variable BASE_URL est absente"

**Solution** : vérifiez que chaque fichier `.env` dans `.env/` contient `BASE_URL=https://...`.

---

### Excel vide ou données manquantes

**Vérifications** :
1. Lisez les messages d'erreur dans la console
2. Vérifiez que votre compte Aruba Central a les permissions API requises
3. Confirmez que la `BASE_URL` correspond bien à votre région

---

### ModuleNotFoundError : `pycentral.classic`

**Cause** : ancienne structure de package utilisée.

**Solution** : assurez-vous d'utiliser la dernière version du code. L'import correct est :
```python
from pycentral.base import ArubaCentralBase   # ✅ Correct (PyPI 1.4.1)
# from pycentral.classic.base import ...      # ❌ Ancienne structure
```

Réinstallez si nécessaire :
```bash
pip uninstall pycentral
pip install arubacentral
```

---

### L'IDE affiche des erreurs d'import mais le script fonctionne

**Cause** : l'IDE utilise un interpréteur Python différent de celui où les packages sont installés.

**VS Code** — sélectionner le bon interpréteur :
1. `Ctrl+Shift+P` → "Python: Select Interpreter"
2. Choisissez l'interpréteur où les packages sont installés
3. Redémarrez VS Code si nécessaire

Ou créez `.vscode/settings.json` :
```json
{
    "python.defaultInterpreterPath": "C:\\chemin\\vers\\python.exe"
}
```

**PyCharm** : `File` → `Settings` → `Project` → `Python Interpreter`.

> **Note** : un avertissement d'import dans l'IDE n'empêche pas l'exécution du script.

---

### Utiliser un environnement virtuel (recommandé)

```bash
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows CMD
venv\Scripts\activate.bat

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```
