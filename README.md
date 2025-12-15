## Aruba Central API Report

Génère un rapport Excel depuis l'API Aruba Central : inventaire des équipements, statut firmware des switches et des points d'accès (swarms), avec calcul automatique des versions maximales disponibles.

### Prérequis

- Python 3.9+
- Accès API Aruba Central (client_id, client_secret, customer_id, etc.)
- Excel (pour ouvrir le fichier généré)

### Installation

Installer les dépendances :

```bash
pip install pycentral requests pandas openpyxl python-dotenv
```

### Configuration multi-clients

Le script supporte plusieurs clients/sites avec des configurations isolées.

#### 1. Créer le dossier de configuration

Créez un dossier `.env` dans `Script Central/` :

```
Script Central/
└── .env/
    ├── Client1.env
    ├── Client2.env
    └── Hermite.env
```

#### 2. Configurer chaque fichier `.env`

Chaque fichier `.env` représente un client et doit contenir les variables suivantes :

```env
CLIENT_ID=votre_client_id
CLIENT_SECRET=votre_client_secret
CUSTOMER_ID=votre_customer_id
CENTRAL_USERNAME=votre_username
CENTRAL_PASSWORD=votre_password
BASE_URL=https://apigw-eucentral3.central.arubanetworks.com
```

**Important** : La `BASE_URL` varie selon la région de votre tenant Aruba Central :
- `https://apigw-eucentral3.central.arubanetworks.com` (EU Central 3)
- `https://eu-apigw.central.arubanetworks.com` (EU)
- `https://apigw-uswest.central.arubanetworks.com` (US West)
- etc.

Le nom du fichier (sans l'extension `.env`) sera utilisé comme nom du client dans le script.

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

### Structure du projet

```
Aruba-Central-API-Report/
├── Script Central/
│   ├── .env/                        # Dossier de configuration des clients
│   │   ├── Client1.env
│   │   └── Client2.env
│   ├── temp/                        # Tokens isolés par client
│   │   ├── Client1/
│   │   └── Client2/
│   ├── Report/                      # Rapports Excel générés
│   │   ├── Client1.xlsx
│   │   └── Client2.xlsx
│   ├── main.py                      # Point d'entrée
│   ├── data_pipeline.py             # Collecte et transformation des données
│   ├── excel_export.py              # Génération du fichier Excel
│   ├── central_config.py            # Chargement des configurations clients
│   ├── clients_config.py            # Détection automatique des clients
│   ├── script_inventaire.py         # Récupération de l'inventaire
│   ├── script_firmware_switch.py    # Firmware des switches
│   ├── script_firmware_swarms.py    # Firmware des swarms (VC + APs)
│   ├── script_firmware_versions.py # Récupération des versions disponibles
│   ├── script_list_switches.py      # Liste des switches (stack/standalone)
│   ├── script_list_gateways.py      # Liste des gateways et récupération des versions recommandées
│   ├── script_load_token.py         # Chargement des tokens
│   └── excel_format.py              # Formatage Excel
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

#### "La variable BASE_URL est absente"

**Solution** :
- Vérifiez que chaque fichier `.env` contient bien la ligne `BASE_URL=https://...`
- La `BASE_URL` doit correspondre à la région de votre tenant Aruba Central

#### Excel vide ou données manquantes

**Vérifications** :
- Vérifiez les messages d'erreur dans la console
- Assurez-vous que votre compte Aruba Central a les permissions nécessaires
- Vérifiez que la `BASE_URL` est correcte pour votre région

### Notes techniques

- Le SDK `ArubaCentralBase` gère automatiquement l'authentification et le rafraîchissement des tokens
- Les appels API directs utilisent la `BASE_URL` du client sélectionné pour garantir la cohérence
- Les tokens sont stockés dans des dossiers séparés par client pour éviter les conflits
- Le script affiche la `BASE_URL` utilisée et les endpoints appelés pour faciliter le débogage
