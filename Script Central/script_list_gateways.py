"""
Module pour lister les gateways via l'API monitoring/v1/gateways.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from script_load_token import get_access_token, load_token


def _recuperer_page_gateways(
    base_url: str,
    headers: Dict[str, str],
    params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Récupère une page de gateways et retourne la liste brute."""
    endpoint = base_url.rstrip("/") + "/monitoring/v1/gateways"
    response = requests.get(endpoint, headers=headers, params=params)
    if response.status_code != 200:
        raise ValueError(f"❌ Erreur {response.status_code}: {response.text}")

    payload = response.json() if response.text else {}
    gateways = payload.get("gateways") or payload.get("data") or []
    return gateways


def _recuperer_details_gateway(
    base_url: str,
    headers: Dict[str, str],
    serial: str,
) -> Optional[Dict[str, Any]]:
    """
    Récupère les détails d'un gateway spécifique par son numéro de série.
    Utilise l'endpoint /monitoring/v1/gateways/{serial}
    """
    endpoint = base_url.rstrip("/") + f"/monitoring/v1/gateways/{serial}"
    try:
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            return response.json() if response.text else {}
        elif response.status_code == 404:
            # Gateway non trouvé, retourner None silencieusement
            return None
        else:
            # Autre erreur, afficher un avertissement mais continuer
            print(f"⚠️ Erreur {response.status_code} pour gateway {serial}: {response.text[:100]}")
            return None
    except Exception as err:
        print(f"⚠️ Exception lors de la récupération du gateway {serial}: {err}")
        return None


def lister_gateways(
    base_url: str,
    group: Optional[str] = None,
    label: Optional[str] = None,
    limit: int = 100,
) -> pd.DataFrame:
    """
    Liste les gateways depuis l'API Aruba Central.

    Parameters
    ----------
    base_url : str
        URL de base Aruba Central (ex: https://apigw-prod2.central.arubanetworks.com)
    group : Optional[str]
        Filtre sur un groupe (group ou label sont exclusifs côté API)
    label : Optional[str]
        Filtre sur un label
    limit : int
        Nombre d'entrées par page (pagination)
    """
    if not base_url:
        raise ValueError("La base URL Aruba Central doit être fournie pour lister les gateways.")

    token_payload = load_token()
    access_token = get_access_token(token_payload)

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",
    }

    params_base: Dict[str, Any] = {"limit": limit}
    if group:
        params_base["group"] = group
    if label:
        params_base["label"] = label

    offset = 0
    tous_gateways: List[Dict[str, Any]] = []

    while True:
        params = {**params_base, "offset": offset}
        gateways = _recuperer_page_gateways(base_url=base_url, headers=headers, params=params)
        if not gateways:
            break

        tous_gateways.extend(gateways)
        if len(gateways) < limit:
            break
        offset += limit

    if not tous_gateways:
        return pd.DataFrame()

    df = pd.json_normalize(tous_gateways)

    # Convertir les listes en chaînes de caractères pour l'affichage Excel
    # (notamment pour le champ "labels" qui peut être une liste)
    if "labels" in df.columns:
        df["labels"] = df["labels"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) and x else (x if x else "")
        )

    # Ordre des colonnes basé sur l'exemple fourni
    columns_order = [
        "serial",
        "macaddr",
        "name",
        "ip_address",
        "model",
        "device_type",
        "status",
        "mode",
        "group_name",
        "site",
        "firmware_version",
        "firmware_backup_version",
        "recommended",  # Ajouter recommended si présent dans la réponse API
        "cpu_utilization",
        "mem_total",
        "mem_free",
        "uptime",
        "reboot_reason",
        "role",
        "mac_range",
        "labels",
    ]

    # Ajouter les colonnes manquantes avec None
    for col in columns_order:
        if col not in df.columns:
            df[col] = None

    # Sélectionner uniquement les colonnes dans l'ordre souhaité
    df = df[columns_order]

    return df


def enrichir_gateways_recommended(
    df_gateways: pd.DataFrame,
    base_url: str,
) -> pd.DataFrame:
    """
    Enrichit le DataFrame des gateways avec la colonne 'recommended' 
    en appelant l'endpoint /monitoring/v1/gateways/{serial} pour chaque gateway.
    """
    if df_gateways is None or df_gateways.empty:
        return df_gateways

    if "serial" not in df_gateways.columns:
        print("⚠️ Colonne 'serial' absente, impossible d'enrichir les gateways")
        df_gateways["recommended"] = None
        return df_gateways

    token_payload = load_token()
    access_token = get_access_token(token_payload)

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",
    }

    # Initialiser la colonne recommended
    df_gateways = df_gateways.copy()
    df_gateways["recommended"] = None

    # Récupérer les détails pour chaque gateway
    total = len(df_gateways)
    print(f"📡 Récupération des versions recommandées pour {total} gateway(s)...")
    
    count_recommended = 0
    for idx, row in df_gateways.iterrows():
        serial = row.get("serial")
        if not serial or pd.isna(serial):
            continue

        details = _recuperer_details_gateway(base_url=base_url, headers=headers, serial=str(serial))
        if details:
            # Extraire le champ recommended_version de la réponse API
            # Le champ s'appelle "recommended_version" dans l'API Aruba Central
            recommended = details.get("recommended_version")
            if recommended:
                df_gateways.at[idx, "recommended"] = recommended
                count_recommended += 1

    print(f"✅ {count_recommended}/{total} gateway(s) avec version recommandée trouvée(s)")
    return df_gateways

