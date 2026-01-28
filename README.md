## Aruba Central API Report

Génère un rapport Excel depuis l'API Aruba Central : inventaire des équipements, statut firmware des switches et des points d'accès (swarms), avec calcul automatique des versions maximales disponibles.

### Prérequis

- Python 3.9+
- Accès API Aruba Central (client_id, client_secret, customer_id, etc.)
- Excel (pour ouvrir le fichier généré)

### Installation

#### Installation automatique (Windows PowerShell)

Exécutez le script d'installation PowerShell à la racine du projet :

```powershell
.\install.ps1
```

Le script va :
- Vérifier si Python 3.9+ est installé
- Installer ou mettre à jour pip
- Installer automatiquement toutes les dépendances nécessaires

#### Installation manuelle

Si vous préférez installer manuellement, assurez-vous d'avoir Python 3.9+ installé, puis installez les dépendances :

**Option 1 : Utiliser le fichier requirements.txt (recommandé)**

```bash
pip install -r requirements.txt
```

**Option 2 : Installation manuelle**

```bash
pip install arubacentral requests pandas openpyxl python-dotenv
```

**⚠️ Note importante sur la structure du package** :

La version de `pycentral` depuis PyPI (1.4.1) utilise une structure différente de l'ancienne version :
- ✅ **PyPI (1.4.1)** : `from pycentral.base import ArubaCentralBase`
- ❌ **Ancienne structure** : `from pycentral.classic.base import ArubaCentralBase`

Le code a été mis à jour pour utiliser la structure PyPI. Si vous obtenez des erreurs d'import, assurez-vous d'utiliser la dernière version du code.

### Configuration multi-clients

Le script supporte plusieurs clients/sites avec des configurations isolées.

#### 1. Créer le fichier `auth.env` principal

Créez un fichier `auth.env` à la racine de `Script Central/` contenant uniquement les identifiants :

```env
CENTRAL_USERNAME=votre_username
CENTRAL_PASSWORD=votre_password
```

#### 2. Créer le dossier de configuration des clients

Créez un dossier `.env` dans `Script Central/` :

```
Script Central/
├── auth.env                # Fichier principal avec username/password
└── .env/
    ├── Client1.env
    ├── Client2.env
    └── Hermite.env
```

#### 3. Configurer chaque fichier `.env` de client

Chaque fichier `.env` dans le dossier `.env/` représente un client et doit contenir les variables suivantes :

```env
CLIENT_ID=votre_client_id
CLIENT_SECRET=votre_client_secret
CUSTOMER_ID=votre_customer_id
BASE_URL=https://apigw-eucentral3.central.arubanetworks.com
```

**Important** : La `BASE_URL` varie selon la région de votre tenant Aruba Central :
- `https://apigw-eucentral3.central.arubanetworks.com` (EU Central 3)
- `https://eu-apigw.central.arubanetworks.com` (EU)
- `https://apigw-uswest.central.arubanetworks.com` (US West)
- etc.

Le nom du fichier (sans l'extension `.env`) sera utilisé comme nom du client dans le script.

**Note** : Les identifiants (`CENTRAL_USERNAME` et `CENTRAL_PASSWORD`) sont partagés entre tous les clients et sont chargés depuis le fichier `auth.env` principal.

### Gestion des tokens

#### Isolation par client

Chaque client a son propre dossier de tokens pour éviter les conflits entre sites :

```
Script Central/
└── temp/
    ├── Client1/          ← Tokens pour Client1
    │   └── tok_*.json
    ├── Client2/          ← Tokens pour Client2
    │   └── tok_*.json
    └── Hermite/          ← Tokens pour Hermite
        └── tok_*.json
```

**Avantages** :
- Pas de conflit entre différents sites/clients
- Tokens persistants et réutilisés entre les exécutions
- Nettoyage simple : supprimez `temp/<nom_client>/` pour forcer une nouvelle authentification

#### Chargement automatique

Le script définit automatiquement la variable d'environnement `CENTRAL_TOKEN_DIR` pour pointer vers le dossier du client sélectionné. Les modules utilisent automatiquement le bon token.

### Utilisation

Exécuter le script principal :

```bash
python "Script Central/main.py"
```

Le script vous demandera de sélectionner un client parmi ceux disponibles dans le dossier `.env/`.

#### Fonctionnalités

Le script génère un rapport Excel avec les feuilles suivantes :

1. **Firmware Consolidé** (première feuille)
   - Vue unifiée des switches, Virtual Controllers (VC) et gateways
   - Colonnes : serial, mac_address, hostname, model, firmware_version, recommended, firmware_max

2. **Inventaire**
   - Liste complète des équipements

3. **Switches (Stack)**
   - Liste issue de l'endpoint `monitoring/v1/switches`
   - Distinction des équipements en stack vs standalone grâce à `stack_status`, `stack_id`, `stack_role`, `stack_member_id`

3. **Firmware Switch**
   - Détails des switches (HP et CX)
   - Calcul automatique de `firmware_max` pour les modèles 2930F (HP) et 6300 (CX)

4. **Gateways**
   - Liste des gateways avec leurs informations détaillées
   - Récupération de la version recommandée via l'endpoint `/monitoring/v1/gateways/{serial}`
   - Calcul automatique de `firmware_max` pour les gateways dans la même branche de version

5. **Firmware Swarms**
   - Virtual Controllers (VC) et tous les points d'accès associés
   - Calcul automatique de `firmware_max` pour les IAP dans la même branche de version

#### Calcul des versions maximales

Le script calcule automatiquement la version maximale disponible (`firmware_max`) dans la même branche :
- **IAP** : Reste dans la même branche majeure/mineure (ex: 8.13.x.x pour 8.13.0.0)
- **Switches 2930F** : Versions HP disponibles
- **Switches 6300** : Versions CX disponibles
- **Gateways** : 
  - Recherche des versions disponibles (type `CONTROLLER`) et sélection de la plus haute dans la même branche
  - Gestion du format spécial des versions gateway (ex: `8.7.0.0-2.3.0.9`) en comparant la partie principale et la partie secondaire
  - Récupération de la version recommandée depuis l'API pour chaque gateway individuellement

### Rapports MRT (Monitoring Reports & Troubleshooting)

Le projet inclut également un script dédié pour générer des rapports via les **APIs MRT** d'Aruba Central, similaires au rapport "Lhermite Agri- Rapport".

⚠️ **IMPORTANT** : Les scripts MRT utilisent la **nouvelle authentification OAuth2 pour New Central**, distincte des autres scripts du projet. Ils ne nécessitent pas `pycentral.base.ArubaCentralBase`.

#### Utilisation du script MRT

Exécuter le script principal MRT :

```bash
python "Script Central/main_mrt.py"
```

Le script vous demandera de :
1. Sélectionner un client parmi ceux disponibles
2. Choisir une période de recherche (7, 30, 90 jours ou personnalisée)

#### Fonctionnalités MRT

Le script MRT permet de :

1. **Lister les rapports générés**
   - Récupère tous les rapports générés disponibles dans Aruba Central
   - Filtre par période (derniers N jours)
   - Affiche les métadonnées des rapports (date, type, statut, etc.)

2. **Lister les rapports programmés**
   - Affiche tous les rapports programmés (scheduled reports)
   - Inclut la configuration de chaque rapport programmé

3. **Export Excel**
   - Génère un fichier Excel avec deux feuilles :
     - **Rapports Générés** : Liste des rapports générés avec leurs métadonnées
     - **Rapports Programmés** : Liste des rapports programmés avec leurs configurations

#### Endpoints API utilisés

Le script utilise les endpoints suivants de l'API Reports d'Aruba Central :
- `GET /reports/api/v1/{customer_id}/generated` - Liste des rapports générés
- `GET /reports/api/v1/{customer_id}/scheduled` - Liste des rapports programmés
- `GET /reports/api/v1/{customer_id}/generated/{report_id}` - Détails d'un rapport spécifique

#### Exemple de sortie

Le fichier Excel généré contiendra des informations comme :
- ID du rapport
- Type de rapport
- Date de génération
- Statut du rapport
- Paramètres de filtrage
- URL de téléchargement (si disponible)
- Configuration de planification (pour les rapports programmés)

#### Authentification OAuth2 pour New Central

Les scripts MRT utilisent une **authentification OAuth2 distincte** pour New Central :

- **URL du token** : `https://sso.common.cloud.hpe.com/as/token.oauth2`
- **Grant type** : `client_credentials`
- **Méthode** : Utilise `BackendApplicationClient` et `OAuth2Session` de `requests_oauthlib`

**Dépendances supplémentaires requises** :
```bash
pip install oauthlib requests-oauthlib
```

#### Notes importantes

- Les rapports MRT nécessitent que votre compte Aruba Central ait les permissions appropriées
- La période de recherche peut être ajustée selon vos besoins
- Les rapports sont filtrés par `customer_id` configuré dans le fichier `.env` du client
- Les scripts MRT sont **indépendants** des autres scripts et n'utilisent pas `ArubaCentralBase`
- L'authentification OAuth2 est effectuée à chaque appel API (pas de cache de token)

### Structure du projet

```
Aruba-Central-API-Report/
├── Script Central/
│   ├── .env                          # Fichier principal avec username/password
│   ├── .env/                         # Dossier de configuration des clients
│   │   ├── Client1.env
│   │   └── Client2.env
│   ├── temp/                         # Tokens isolés par client
│   │   ├── Client1/
│   │   └── Client2/
│   ├── Report/                       # Rapports Excel générés
│   │   ├── Client1.xlsx
│   │   └── Client2.xlsx
│   ├── main.py                       # Point d'entrée
│   ├── data_pipeline.py              # Collecte et transformation des données
│   ├── excel_export.py               # Génération du fichier Excel
│   ├── central_config.py             # Chargement des configurations clients
│   ├── clients_config.py             # Détection automatique des clients
│   ├── script_inventaire.py          # Récupération de l'inventaire
│   ├── script_firmware_switch.py     # Firmware des switches
│   ├── script_firmware_swarms.py     # Firmware des swarms (VC + APs)
│   ├── script_firmware_versions.py   # Récupération des versions disponibles
│   ├── script_list_switches.py       # Liste des switches (stack/standalone)
│   ├── script_list_gateways.py       # Liste des gateways et récupération des versions recommandées
│   ├── script_load_token.py          # Chargement des tokens
│   ├── script_mrt_reports.py         # Rapports MRT (Monitoring Reports & Troubleshooting)
│   ├── main_mrt.py                   # Point d'entrée pour les rapports MRT
│   └── excel_format.py               # Formatage Excel
└── README.md
```

### Bonnes pratiques

- **Sécurité** : Ne versionnez jamais vos fichiers `.env` contenant les identifiants
- **Tokens** : Les tokens sont automatiquement isolés par client, pas besoin de les gérer manuellement
- **Base URL** : Vérifiez que la `BASE_URL` dans chaque `.env` correspond à la région de votre tenant
- **Nettoyage** : Supprimez `temp/<nom_client>/` si vous rencontrez des problèmes d'authentification

### Dépannage

#### Erreur 401 : "The access token is invalid or has expired"

**Causes possibles** :
1. Le token a été généré avec une autre `BASE_URL` que celle du client sélectionné
2. Le token a expiré

**Solution** :
- Supprimez le dossier `temp/<nom_client>/` pour forcer la régénération du token
- Vérifiez que la `BASE_URL` dans le fichier `.env` correspond bien à votre tenant

#### "Aucun client n'est configuré"

**Solution** :
- Vérifiez que le dossier `Script Central/.env/` existe
- Ajoutez au moins un fichier `.env` dans ce dossier (ex: `Client1.env`)

#### "Le fichier auth.env principal est introuvable"

**Solution** :
- Créez un fichier `auth.env` à la racine de `Script Central/` avec `CENTRAL_USERNAME` et `CENTRAL_PASSWORD`

#### "La variable BASE_URL est absente"

**Solution** :
- Vérifiez que chaque fichier `.env` dans le dossier `.env/` contient bien la ligne `BASE_URL=https://...`
- La `BASE_URL` doit correspondre à la région de votre tenant Aruba Central

#### Excel vide ou données manquantes

**Vérifications** :
- Vérifiez les messages d'erreur dans la console
- Assurez-vous que votre compte Aruba Central a les permissions nécessaires
- Vérifiez que la `BASE_URL` est correcte pour votre région

#### Erreur : "Import 'pycentral.classic.base' could not be resolved" ou "ModuleNotFoundError: No module named 'pycentral.classic'"

**Causes possibles** :
1. Le mauvais package est installé (`pycentral` au lieu de `arubacentral`)
2. Le package `arubacentral` n'est pas installé
3. Installation dans un environnement Python différent de celui utilisé par l'IDE
4. Problème avec l'environnement virtuel

**Solutions** :

1. **Vérifier quel package est installé** :
   ```bash
   pip show pycentral
   ```
   
2. **Réinstaller pycentral correctement** :
   Le package `pycentral` doit avoir la structure `classic.base`. Si ce n'est pas le cas, réinstallez-le :
   ```bash
   pip uninstall pycentral
   pip install pycentral==1.4.1
   ```
   
   Ou installez depuis le dépôt GitHub officiel d'Aruba :
   ```bash
   pip uninstall pycentral
   pip install git+https://github.com/aruba/pycentral.git
   ```

2. **Réinstaller toutes les dépendances** :
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
   Ou manuellement :
   ```bash
   pip install --upgrade pycentral requests pandas openpyxl python-dotenv
   ```

3. **Vérifier l'environnement Python utilisé** :
   
   **Le problème vient souvent du fait que l'IDE utilise un interpréteur Python différent de celui où les packages sont installés.**
   
   **Pour VS Code** :
   1. Ouvrez la palette de commandes : `Ctrl+Shift+P` (ou `Cmd+Shift+P` sur Mac)
   2. Tapez "Python: Select Interpreter"
   3. Sélectionnez l'interpréteur Python où les packages sont installés
      - D'après votre sortie pip, c'est : `C:\Users\ldescours\AppData\Local\Programs\Python\Python314\python.exe`
   4. Vérifiez dans la barre d'état en bas de VS Code que le bon interpréteur est sélectionné
   5. Redémarrez VS Code si nécessaire
   
   **Pour PyCharm** :
   1. Allez dans `File` → `Settings` (ou `PyCharm` → `Preferences` sur Mac)
   2. Allez dans `Project` → `Python Interpreter`
   3. Sélectionnez l'interpréteur Python où les packages sont installés
   4. Cliquez sur `Apply` et `OK`
   
   **Vérification rapide** :
   ```bash
   # Vérifier quel Python est utilisé
   python --version
   where python  # Sur Windows
   which python  # Sur Linux/Mac
   
   # Vérifier que pycentral est accessible depuis ce Python
   python -c "import pycentral; print('OK: pycentral est installé')"
   
   # Vérifier l'import spécifique utilisé dans le projet
   python -c "from pycentral.base import ArubaCentralBase; print('OK: Import réussi')"
   ```

4. **Utiliser un environnement virtuel (recommandé)** :
   ```bash
   # Créer un environnement virtuel
   python -m venv venv
   
   # Activer l'environnement virtuel
   # Sur Windows PowerShell :
   .\venv\Scripts\Activate.ps1
   # Sur Windows CMD :
   venv\Scripts\activate.bat
   # Sur Linux/Mac :
   source venv/bin/activate
   
   # Installer les dépendances
   pip install -r requirements.txt
   ```

5. **Vérifier que pycentral est bien installé avec la bonne structure** :
   ```bash
   python -c "import pycentral; print('OK: pycentral est installé')"
   ```
   Ou pour vérifier les imports spécifiques :
   ```bash
   python -c "from pycentral.base import ArubaCentralBase; print('OK: Import réussi')"
   ```
   Si cela fonctionne dans le terminal mais pas dans l'IDE, le problème vient de la configuration de l'IDE (voir point 3 ci-dessus).
   
   **Si vous obtenez "ModuleNotFoundError: No module named 'pycentral.classic'"** :
   
   **C'est normal !** La version de `pycentral` depuis PyPI (1.4.1) utilise une structure différente :
   - ✅ **Correct (PyPI)** : `from pycentral.base import ArubaCentralBase`
   - ❌ **Ancienne structure** : `from pycentral.classic.base import ArubaCentralBase`
   
   Le code a été mis à jour pour utiliser la structure PyPI. Si vous avez encore des erreurs, assurez-vous d'utiliser la dernière version du code qui utilise `from pycentral.base import ArubaCentralBase`.

6. **Solution rapide si l'IDE ne détecte toujours pas les packages** :
   
   **Dans VS Code** :
   - Fermez VS Code complètement
   - Ouvrez un terminal PowerShell dans le dossier du projet
   - Exécutez : `code .` pour ouvrir VS Code depuis le terminal avec le bon environnement
   - Ou créez un fichier `.vscode/settings.json` dans le projet avec :
     ```json
     {
         "python.defaultInterpreterPath": "C:\\Users\\ldescours\\AppData\\Local\\Programs\\Python\\Python314\\python.exe"
     }
     ```
     (Remplacez le chemin par votre chemin Python si différent)
   
   **Note importante** : L'avertissement "could not be resolved" dans l'IDE n'empêche généralement pas l'exécution du script. Si le script fonctionne quand vous l'exécutez (`python main.py`), c'est juste un problème d'affichage dans l'IDE.

### Notes techniques

- Le SDK `ArubaCentralBase` gère automatiquement l'authentification et le rafraîchissement des tokens
- Les appels API directs utilisent la `BASE_URL` du client sélectionné pour garantir la cohérence
- Les tokens sont stockés dans des dossiers séparés par client pour éviter les conflits
- Le script affiche la `BASE_URL` utilisée et les endpoints appelés pour faciliter le débogage
