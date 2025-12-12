"""
Module pour récupérer le statut du firmware des switches depuis Aruba Central.

Ce module utilise directement l'API REST d'Aruba Central (endpoint firmware/v1/devices)
pour récupérer les informations de firmware des switches, contrairement aux autres
modules qui utilisent le SDK pycentral.
"""

from typing import Optional
from script_load_token import load_token, get_access_token
import requests
import pandas as pd


def get_firmware_switch(
    conn,
    device_type: Optional[str] = None,
    limit: Optional[int] = None,
    base_url: Optional[str] = None,
) -> pd.DataFrame:
    """
    Récupère le statut du firmware des switches depuis l'API Aruba Central.
    
    Cette fonction utilise directement l'API REST d'Aruba Central pour obtenir
    les informations de firmware des switches. Elle permet de filtrer par type
    d'équipement et de limiter le nombre de résultats.
    
    Parameters
    ----------
    conn : Any
        Paramètre non utilisé (conservé pour compatibilité avec les autres fonctions)
    device_type : Optional[str]
        Filtre par type d'équipement (ex: "HP" pour les switches HP)
        Si None, tous les types d'équipements sont inclus
    limit : Optional[int]
        Nombre maximum de résultats à retourner
        Si None, aucune limite n'est appliquée
    
    Returns
    -------
    pd.DataFrame
        DataFrame contenant les informations de firmware des switches avec les colonnes :
        - serial, mac_address, hostname, model
        - is_reboot_enable, device_status
        - firmware_version, recommended, upgrade_required, is_stack
        - status.state, status.reason
        Retourne un DataFrame vide si aucun équipement n'est trouvé.
    
    Raises
    ------
    ValueError
        Si l'appel API échoue (code de statut HTTP != 200)
    """
    # Chargement du token d'authentification depuis le fichier JSON
    token_payload = load_token()
    # Extraction du token d'accès depuis le payload
    access_token = get_access_token(token_payload)

    # URL de base de l'API firmware d'Aruba Central
    if not base_url:
        raise ValueError("La base URL Aruba Central doit être fournie pour les switches.")
    endpoint = base_url.rstrip("/") + "/firmware/v1/devices"
    print(f"🔗 Appel API switches : {endpoint}")
    
    # Construction des paramètres de requête
    params = {}
    if device_type is not None:
        params["device_type"] = device_type
    if limit is not None:
        params["limit"] = limit

    # En-têtes HTTP pour l'authentification et le format de réponse
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",  # Token d'authentification OAuth
    }

    # Appel GET à l'API pour récupérer les données de firmware
    response = requests.get(endpoint, headers=headers, params=params)
    
    # Vérification du code de statut HTTP
    if response.status_code != 200:
        raise ValueError(f"❌ Erreur {response.status_code}: {response.text}")

    # Conversion de la réponse JSON en dictionnaire Python
    data = response.json()
    # Extraction de la liste des équipements depuis la réponse
    devices = data.get("devices", [])

    # Retour d'un DataFrame vide si aucun équipement n'est trouvé
    if not devices:
        return pd.DataFrame()

    # Normalisation du JSON pour aplatir les structures imbriquées (ex: status.state, status.reason)
    # Cela permet de convertir les objets JSON complexes en colonnes plates dans le DataFrame
    df = pd.json_normalize(devices)

    # Définition d'un ordre de colonnes clair et logique pour l'affichage
    columns_order = [
        "serial", "mac_address", "hostname", "model",           # Informations de base
        "is_reboot_enable", "device_status",                    # Statut de l'équipement
        "firmware_version", "recommended", "upgrade_required", "is_stack",  # Informations firmware
        "status.state", "status.reason"                         # Détails du statut
    ]

    # Ajout des colonnes manquantes si nécessaire (remplies avec None)
    # Cela garantit que toutes les colonnes attendues existent même si certaines données sont absentes
    for col in columns_order:
        if col not in df.columns:
            df[col] = None

    # Réorganisation des colonnes selon l'ordre défini
    df = df[columns_order]

    # Conversion des valeurs booléennes en texte "Yes"/"No" pour une meilleure lisibilité dans Excel
    for col in ["is_reboot_enable", "upgrade_required", "is_stack"]:
        df[col] = df[col].apply(lambda x: "Yes" if x else "No")

    return df
